#include "modem.h"

static volatile int stream_fd;
static volatile int control_fd;
static struct sockaddr_storage stream_host_addr;
static struct sockaddr_storage stream_local_addr;
static struct sockaddr_storage control_host_addr;
static struct sockaddr_storage control_local_addr;

K_SEM_DEFINE(lte_connected, 1, 1);
K_SEM_DEFINE(connection_configured, 0, 1);
K_SEM_DEFINE(modem_tx_buf_available, 1, 1);
K_SEM_DEFINE(modem_rx_buf_available, 1, 1);

volatile uint8_t modem_rx_buf[65535];
volatile uint8_t modem_tx_buf[65535];
volatile uint16_t modem_rx_len;
volatile uint16_t modem_tx_len;


LOG_MODULE_REGISTER(modem);

int modem_connect_ipv4(uint8_t *conn_details, size_t conn_details_len) {
    int err, status, i;
    uint16_t stream_port, control_port;
    char ip_addr[16];

    // Check for correct length & seperators
    // Expected format: 'E4NNN.NNN.NNN.NNN:SSSSS:CCCCC'
    if ((conn_details_len != 29) || conn_details[5] != '.' || 
            conn_details[9] != '.' || conn_details[13] != '.' || 
            conn_details[17] != ':' || conn_details[23] != ':') {
        LOG_ERR("Invalid connection setup request format");
        return -1;
    }

    // Acquire data from string
    //memcpy(ip_addr, &conn_details[2], 15);
	for (i = 0; i < 15; i++) {
		ip_addr[i] = conn_details[i +2];
	}
	ip_addr[15] = '\0';
	
    stream_port = strtoul(&conn_details[18], NULL, 10);
    control_port = strtoul(&conn_details[24], NULL, 10);

    LOG_INF("IP: %s", ip_addr);
    LOG_INF("Stream port: %u, Control port: %u", stream_port, control_port);

    // Stream address config
    struct sockaddr_in *server0 = ((struct sockaddr_in *)&stream_host_addr);
	server0->sin_family = AF_INET;
	server0->sin_port = htons(stream_port);
	status = inet_pton(AF_INET, ip_addr, &server0->sin_addr);
	if (status == 0) {
		LOG_ERR("src does not contain a character string representing a valid network address");
		return -1;
	} else if(status < 0) {
		LOG_ERR("inet_pton failed: %d %s\n", errno, strerror(errno));
		err = -errno;
		return -1;
	}

	// Stream local address config 
	struct sockaddr_in *server3 = ((struct sockaddr_in *)&stream_local_addr);
	server3->sin_family = AF_INET;
	server3->sin_port = htons(stream_port);
	server3->sin_addr.s_addr = INADDR_ANY;

    // Control send address config
    struct sockaddr_in *server1 = ((struct sockaddr_in *)&control_host_addr);
	server1->sin_family = AF_INET;
	server1->sin_port = htons(control_port);
	status = inet_pton(AF_INET, ip_addr, &server1->sin_addr);
	if (status == 0) {
		LOG_ERR("src does not contain a character string representing a valid network address");
		return -1;
	} else if(status < 0) {
		LOG_ERR("inet_pton failed: %d %s\n", errno, strerror(errno));
		err = -errno;
		return -1;
	}
	// Control local address config 
	struct sockaddr_in *server2 = ((struct sockaddr_in *)&control_local_addr);
	server2->sin_family = AF_INET;
	server2->sin_port = htons(control_port);
	server2->sin_addr.s_addr = INADDR_ANY;
    
    // Stream socket bind/connect
    stream_fd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
	if (stream_fd < 0) {
		LOG_ERR("Failed to create stream UDP socket, error: %d", errno);
		err = -errno;
		return err;
	}
	err = bind(stream_fd, (struct sockaddr *)&stream_local_addr, sizeof(struct sockaddr_in));
	if (err < 0) {
		printk("Bind failed : %d %s\n", errno, strerror(errno));
		err = -errno;
		return err;
	}
	err = connect(stream_fd, (struct sockaddr *)&stream_host_addr, sizeof(struct sockaddr_in));
	if (err < 0) {
		LOG_ERR("Failed to connect stream socket, error: %d", errno);
		close(stream_fd);
		return err;
	}

	// Control socket bind/connect and listen
	control_fd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
	if (control_fd < 0) {
		LOG_ERR("Failed to create control UDP socket, error: %d", errno);
		err = -errno;
		return err;
	}
	err = bind(control_fd, (struct sockaddr *)&control_local_addr, sizeof(struct sockaddr_in));
	if (err < 0) {
		printk("Bind failed : %d %s\n", errno, strerror(errno));
		err = -errno;
		return err;
	}
	err = connect(control_fd, (struct sockaddr *)&control_host_addr, sizeof(struct sockaddr_in));
	if (err < 0) {
		LOG_ERR("Failed to connect control socket, error: %d", errno);
		close(control_fd);
		return err;
	}

    k_sem_give(&connection_configured);
    return 0;
}



static void lte_handler(const struct lte_lc_evt *const evt) {
	switch (evt->type) {
	case LTE_LC_EVT_NW_REG_STATUS:
		if ((evt->nw_reg_status != LTE_LC_NW_REG_REGISTERED_HOME) &&
		    (evt->nw_reg_status != LTE_LC_NW_REG_REGISTERED_ROAMING)) {
			break;
		}

		LOG_INF("Network registration status: %s",
			evt->nw_reg_status == LTE_LC_NW_REG_REGISTERED_HOME ?
			"Connected - home" : "Connected - roaming");
		k_sem_take(&lte_connected, K_NO_WAIT);
		break;
	case LTE_LC_EVT_PSM_UPDATE:
		LOG_INF("PSM parameter update: TAU: %d s, Active time: %d s",
			evt->psm_cfg.tau, evt->psm_cfg.active_time);
		break;
    // case LTE_LC_EVT_EDRX_UPDATE:
    //     LOG_INF("eDRX parameter update: eDRX: %f, PTW: %f",
    //         evt->edrx_cfg.edrx, evt->edrx_cfg.ptw);
    //     break;
    case LTE_LC_EVT_EDRX_UPDATE:
         {
            const char *mode = "none";
            if (evt->edrx_cfg.mode == LTE_LC_LTE_MODE_LTEM) {
               mode = "LTE-M";
            } else if (evt->edrx_cfg.mode == LTE_LC_LTE_MODE_NBIOT) {
               mode = "NB-IoT";
            }
            // LOG_INF("eDRX cell update: %s, eDRX: %f, PTW: %f",
            //         mode, (double)evt->edrx_cfg.edrx, (double)evt->edrx_cfg.ptw);

            LOG_INF("eDRX cell update: %s, eDRX: %d.%03ds, PTW: %d.%03ds", mode,
                (int)evt->edrx_cfg.edrx, (int)((evt->edrx_cfg.edrx - (int)evt->edrx_cfg.edrx) * 1000),
                (int)evt->edrx_cfg.ptw, (int)((evt->edrx_cfg.ptw - (int)evt->edrx_cfg.ptw) * 1000));

            break;
         }
	case LTE_LC_EVT_RRC_UPDATE:
		LOG_INF("RRC mode: %s",
			evt->rrc_mode == LTE_LC_RRC_MODE_CONNECTED ?
			"Connected" : "Idle");
		break;
	case LTE_LC_EVT_CELL_UPDATE:
		LOG_INF("LTE cell changed: Cell ID: %d, Tracking area: %d",
		       evt->cell.id, evt->cell.tac);
		break;
	default:
		break;
	}
}

int modem_init(void) {
	int err;

	err = nrf_modem_lib_init();
	if (err) {
		LOG_ERR("Failed to initialize modem library, error: %d", err);
		return err;
	}
#if defined(CONFIG_UDP_RAI_ENABLE)
	/* Enable Access Stratum RAI support for nRF9160.
	 * Note: The 1.3.x modem firmware release is certified to be compliant with 3GPP Release 13.
	 * %REL14FEAT enables selected optional features from 3GPP Release 14. The 3GPP Release 14
	 * features are not GCF or PTCRB conformance certified by Nordic and must be certified
	 * by MNO before being used in commercial products.
	 * nRF9161 is certified to be compliant with 3GPP Release 14.
	 */

	err = nrf_modem_at_printf("AT%%REL14FEAT=0,1,0,0,0");
	if (err) {
		LOG_ERR("Failed to enable Access Stratum RAI support, error: %d", err);
		return err;
	}
#endif

	return 0;
}

int modem_network_connect(void) {
	int err;

	err = lte_lc_connect_async(lte_handler);
	if (err) {
		LOG_ERR("Failed to connect to LTE network, error: %d", err);
		return err;
	}

	return 0;
}

int modem_send(bool control_message) {
	int err;
	if (control_message) {
		err = send(control_fd, (uint8_t *) modem_tx_buf, modem_tx_len, 0);
	} else {
		err = send(stream_fd, (uint8_t *) modem_tx_buf, modem_tx_len, 0);
	}
	if (err < 0) {
		err = -errno;
		LOG_ERR("send() error: %i", err);
		k_sem_give(&modem_tx_buf_available);
		return err;
	}
	LOG_INF("Bytes TX: %u", modem_tx_len);
	k_sem_give(&modem_tx_buf_available);
	return 0;
}

int modem_downlink_monitor(void) {
    struct sockaddr_storage client_addr;
    int err;
    socklen_t addr_size;
    // sockaddr_in pointers for accessing IP addresses
    struct sockaddr_in *client_addr_in = ((struct sockaddr_in *)&client_addr);
    struct sockaddr_in *control_host_addr_in =
        ((struct sockaddr_in *)&control_host_addr);

    addr_size = sizeof(client_addr);

    k_sem_take(&modem_rx_buf_available, K_FOREVER);
	modem_rx_len = 0;
	// Reserve first 3 bits for type/size header
    modem_rx_len =
        recvfrom(control_fd, (uint8_t *)&modem_rx_buf[3], (sizeof(modem_rx_buf) - 3),
                 0, (struct sockaddr *)&client_addr, &addr_size);
    if (modem_rx_len < 0) {
        err = -errno;
        LOG_ERR("recvfrom() error: %i", err);
        return err;
    } else if (modem_rx_len > 0) {
        // Don't process if not expected server IP or not IPv4
        if (client_addr.ss_family == AF_INET) {
            if (client_addr_in->sin_addr.s_addr !=
                control_host_addr_in->sin_addr.s_addr) {
                LOG_ERR(
                    "Attempted connection from unexpected IP addr: "
                    "%u.%u.%u.%u",
                    client_addr_in->sin_addr.s4_addr[3],
                    client_addr_in->sin_addr.s4_addr[2],
                    client_addr_in->sin_addr.s4_addr[1],
                    client_addr_in->sin_addr.s4_addr[0]);
                LOG_ERR("Expected: %u.%u.%u.%u",
                        control_host_addr_in->sin_addr.s4_addr[3],
                        control_host_addr_in->sin_addr.s4_addr[2],
                        control_host_addr_in->sin_addr.s4_addr[1],
                        control_host_addr_in->sin_addr.s4_addr[0]);
                return -1;
            }
        } else {
            LOG_ERR(
                "IPv6 connection attempted with control receive socket, "
                "not "
                "supported");
            return -1;
        }
        LOG_INF("Bytes RX: %u", modem_rx_len);
		// Set header
		modem_rx_buf[0] = 'C';
		modem_rx_buf[1] = modem_rx_len >> 8;
		modem_rx_buf[2] = modem_rx_len & 0xFF;
		// Adjust for header so serial interface will send correct amount
		modem_rx_len += 3;
        // UART library will forward modem_rx_buf through once it receives
        // ready signal from this wake line assertion
        uart_set_wake(true);
    }
    return 0;
}