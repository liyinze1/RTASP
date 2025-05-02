#ifndef MODEM_H
#define MODEM_H

#include <zephyr/kernel.h>
#include <stdio.h>
#include <modem/lte_lc.h>
#include <zephyr/net/socket.h>
#include <modem/nrf_modem_lib.h>
#include <nrf_modem_at.h>
#include "serial_interface.h"

extern struct k_sem lte_connected;
extern struct k_sem connection_configured;
extern struct k_sem modem_tx_buf_available;
extern struct k_sem modem_rx_buf_available;
extern volatile uint8_t modem_rx_buf[65535];
extern volatile uint8_t modem_tx_buf[65535];
extern volatile uint16_t modem_rx_len;
extern volatile uint16_t modem_tx_len;

int modem_send(bool control_message);
int modem_connect_ipv4(uint8_t *conn_details, size_t conn_details_len);
int modem_init(void);
int modem_network_connect(void);
int modem_downlink_monitor(void);

#endif