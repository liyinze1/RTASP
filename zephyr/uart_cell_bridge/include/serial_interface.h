#ifndef SERIAL_INTERFACE_H
#define SERIAL_INTERFACE_H

#define UART_RX_TIMEOUT_US          2000

#define ZEPHYR_USER_NODE    DT_PATH(zephyr_user)

extern struct k_sem uart_data_ready;

#include "modem.h"
#include <zephyr/kernel.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/logging/log.h>
#include <zephyr/drivers/gpio.h>

void uart_fwd_modem_buf(void);
void uart_init(void);
void uart_send_ack(void);
void uart_send_nack(void);
void uart_send_ready(void);
//void uart_peripheral_enable(void);
//void uart_peripheral_disable(void);
void uart_process_rx(void);
void uart_set_wake(bool state);

#endif