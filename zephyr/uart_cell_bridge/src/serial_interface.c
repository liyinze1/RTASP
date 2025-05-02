#include "serial_interface.h"

static const struct device *uart2_dev = DEVICE_DT_GET(DT_NODELABEL(uart2));

static const struct gpio_dt_spec dev_wake_in = GPIO_DT_SPEC_GET(ZEPHYR_USER_NODE, wakein_gpios);
static const struct gpio_dt_spec dev_wake_out = GPIO_DT_SPEC_GET(ZEPHYR_USER_NODE, wakeout_gpios);

LOG_MODULE_REGISTER(serial);

static struct gpio_callback wakein_cb_data;

static volatile uint8_t uart_rx_buf[65535];
static volatile uint16_t uart_rx_len;
static volatile uint16_t uart_rx_offset;

K_SEM_DEFINE(uart_data_ready, 0, 1);

void static wakein_cb(const struct device *dev, struct gpio_callback *cb,
		    uint32_t pins) {
    LOG_INF("Wake input signal received");

    //TODO: implement power management

    uart_send_ready();
}

void static uart_cb(const struct device *dev, struct uart_event *evt,
             void *user_data) {
    switch (evt->type) {
        case UART_TX_DONE:
            // LOG_INF("UART_TX_DONE");
            break;

        case UART_TX_ABORTED:
            LOG_ERR("UART_TX_ABORTED");
            break;

        case UART_RX_RDY:
            uart_rx_len = evt->data.rx.len;
            uart_rx_offset = evt->data.rx.offset;
            uart_rx_disable(uart2_dev);
			k_sem_give(&uart_data_ready);
            break;

        case UART_RX_BUF_REQUEST:
            // if(uart_rx_buf_rsp(uart2_dev, (uint8_t *)uart_rx_buf, sizeof(uart_rx_buf))) {
            //     LOG_ERR("Couldn't assign UART buffer");
            // }
            break;

        case UART_RX_BUF_RELEASED:
            break;

        case UART_RX_DISABLED:
            if (uart_rx_enable(uart2_dev, (uint8_t *)uart_rx_buf, sizeof(uart_rx_buf),
                               UART_RX_TIMEOUT_US)) {
                LOG_ERR("Couldn't assign UART buffer");
            }
            break;

        case UART_RX_STOPPED:
            LOG_INF("UART_RX_STOPPED, reason: %u", evt->data.rx_stop.reason);
            break;

        default:
            break;
    }
}

void uart_init(void) {
    // Configure wake signal output
    if (!gpio_is_ready_dt(&dev_wake_out)) {
         LOG_ERR("GPIO port %s is not ready!", dev_wake_out.port->name);
	    return;
    }
    gpio_pin_configure_dt(&dev_wake_out, GPIO_OUTPUT_LOW);
    // Configure wake signal input
    if (!gpio_is_ready_dt(&dev_wake_in)) {
         LOG_ERR("GPIO port %s is not ready!", dev_wake_in.port->name);
	    return;
    }
    if (gpio_pin_interrupt_configure_dt(&dev_wake_in, GPIO_INT_EDGE_RISING)) {
        LOG_ERR("Failed to configure interrupt on %s pin %d\n",
			dev_wake_in.port->name, dev_wake_in.pin);
		return;
    }
    gpio_init_callback(&wakein_cb_data, wakein_cb, BIT(dev_wake_in.pin));
	gpio_add_callback(dev_wake_in.port, &wakein_cb_data);

    if (!device_is_ready(uart2_dev)) {
        LOG_ERR("UART device not found!");
        return;
    }
    if (uart_callback_set(uart2_dev, uart_cb, NULL)) {
        LOG_ERR("Couldn't set UART callback function");
        return;
    }
    if (uart_rx_enable(uart2_dev, (uint8_t *)uart_rx_buf, sizeof(uart_rx_buf),
                       UART_RX_TIMEOUT_US)) {
        LOG_ERR("Couldn't assign UART buffer");
        return;
    }
    LOG_INF("UART init success");
}

void uart_send_ack(void) {
    static const uint8_t tx_char = 'A';
    if (uart_tx(uart2_dev, &tx_char, sizeof(tx_char), SYS_FOREVER_US)) {
        LOG_ERR("Couldn't send ACK");
    }
}

void uart_send_nack(void) {
    static const uint8_t tx_char = 'N';
    if (uart_tx(uart2_dev, &tx_char, sizeof(tx_char), SYS_FOREVER_US)) {
        LOG_ERR("Couldn't send NACK");
    }
}

void uart_send_ready(void) {
    static const uint8_t tx_char = 'R';
    if (uart_tx(uart2_dev, &tx_char, sizeof(tx_char), SYS_FOREVER_US)) {
        LOG_ERR("Couldn't send Ready");
    }
}

void uart_fwd_modem_buf(void) {
    if (uart_tx(uart2_dev, (uint8_t *) modem_rx_buf, modem_rx_len, SYS_FOREVER_US)) {
        LOG_ERR("Couldn't forward modem rx buf");
    }
    LOG_INF("Bytes TX: %u", modem_rx_len);
}

void uart_set_wake(bool state) {
    if (state) {
        LOG_INF("Set wake output high");
        gpio_pin_set_dt(&dev_wake_out, 1);
    } else {
        LOG_INF("Set wake output low");
        gpio_pin_set_dt(&dev_wake_out, 0);
    }
}

void uart_process_rx(void) {
    LOG_INF("current offset %d, current length %d", uart_rx_offset, uart_rx_len);
    // return;
    uint16_t payload_len_specd;
    uint8_t connection_info[29];
    if (uart_rx_len >= 1) {
        switch (uart_rx_buf[(uart_rx_offset + 0) % sizeof(uart_rx_buf)]) {
            case 'E':
                if (uart_rx_buf[(uart_rx_offset + 1) % sizeof(uart_rx_buf)] == '4') {
                    LOG_INF("Received IPv4 connection setup request");
                    for (size_t i = 0; i < 29; i++) {
                        connection_info[i] = uart_rx_buf[(uart_rx_offset + i) % sizeof(uart_rx_buf)];
                    }
                    if (modem_connect_ipv4(connection_info, sizeof(connection_info))) {
                        uart_send_nack();
                    } else {
                        uart_send_ack();
                    }
                } else if (uart_rx_buf[(uart_rx_offset + 1) % sizeof(uart_rx_buf)] == '6') {
                    LOG_INF("Received IPv6 connection setup request");
                    LOG_ERR("IPv6 connection support still to be implemented");

                    uart_send_nack();
                } else {
                    LOG_ERR("Unknown connection setup request");
                    uart_send_nack();
                }
                break;

            case 'C':
                LOG_INF("Bytes RX: %u (CTL)", uart_rx_len);
                if (k_sem_count_get(&connection_configured)) {
                    LOG_ERR("No connection configured");
                    uart_send_nack();
                    break;
                }
                payload_len_specd =  (uart_rx_buf[(uart_rx_offset + 1) % sizeof(uart_rx_buf)] << 8) | uart_rx_buf[(uart_rx_offset + 2) % sizeof(uart_rx_buf)];
                if (payload_len_specd != uart_rx_len - 3) {
                    LOG_ERR("Message specified length %u doesn't match rx'd %u", payload_len_specd, uart_rx_len - 3);
                    uart_send_nack();
                    break;
                }
                if (k_sem_take(&modem_tx_buf_available, K_SECONDS(10))) {
                    LOG_ERR("Failed to access modem tx buffer");
                    uart_send_nack();
                    break;
                }
                // Trim message type and length (first 3 bytes)
                for (size_t i = 0; i < (uart_rx_len - 3); i++) {
                    modem_tx_buf[i] = uart_rx_buf[(uart_rx_offset + i + 3) % sizeof(uart_rx_buf)];
                }
                modem_tx_len = uart_rx_len - 3;
                uart_send_ack();
                modem_send(true);
                break;

            case 'S':
                LOG_INF("Bytes RX: %u (STR)", uart_rx_len);
                if (k_sem_count_get(&connection_configured)) {
                    LOG_ERR("No connection configured");
                    uart_send_nack();
                    break;
                }
                payload_len_specd =  (uart_rx_buf[(uart_rx_offset + 1) % sizeof(uart_rx_buf)] << 8) | uart_rx_buf[(uart_rx_offset + 2) % sizeof(uart_rx_buf)];
                if (payload_len_specd != uart_rx_len - 3) {
                    LOG_ERR("Message specified length %u doesn't match rx'd %u", payload_len_specd, uart_rx_len - 3);
                    uart_send_nack();
                    break;
                }
                if (k_sem_take(&modem_tx_buf_available, K_SECONDS(10))) {
                    LOG_ERR("Failed to access modem tx buffer");
                    uart_send_nack();
                    break;
                }
                // Trim message type and length (first 3 bytes)
                for (size_t i = 0; i < (uart_rx_len - 3); i++) {
                    modem_tx_buf[i] = uart_rx_buf[(uart_rx_offset + i + 3) % sizeof(uart_rx_buf)];
                }
                modem_tx_len = uart_rx_len - 3;
                uart_send_ack();
                modem_send(false);
                break;
            case 'R':
                if(modem_rx_len <= 0) {
                    LOG_ERR("Received unexpected ready signal, nothing to forward");
                } else {
                    LOG_INF("Received ready signal");
                    uart_set_wake(0);
                    uart_fwd_modem_buf();
                    k_sem_give(&modem_rx_buf_available);
                }
                break;

            case '?':
                LOG_INF("Received network status query");
                if (k_sem_count_get(&lte_connected) == 0) {
                    uart_send_ack();
                } else {
                    uart_send_nack();
                }
                break;

            default:
                LOG_ERR("Received unknown message type");
                uart_send_nack();
                break;
        }
    }
    // Re enable UART after processing packet
    // err = uart_rx_enable(uart2_dev, (uint8_t *)uart_rx_buf, sizeof(uart_rx_buf),
    //                    UART_RX_TIMEOUT_US);
    // if (err) {
    //     LOG_ERR("Couldn't assign UART buffer %i", err);
    // }
}