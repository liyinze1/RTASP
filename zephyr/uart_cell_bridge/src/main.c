#include <zephyr/kernel.h>
#include <ncs_version.h>
#include "serial_interface.h"
#include "modem.h"

// Force specific version of nRF Connect SDK
#if NCS_VERSION_NUMBER != 0x20600
#error Please build with nRF Connect SDK v2.6.0 to guarantee functionality
#endif

// Thread parameters
#define STACKSIZE 512
#define THREAD_UARTPROCESS_PRIORITY 6
#define THREAD_CELLRECV_PRIORITY 7

// Thread function protoypes
void thread_uartprocess (void);
void thread_cellrecv (void);

// Thread creation 
K_THREAD_DEFINE(thread_uartprocess_id, STACKSIZE, thread_uartprocess, NULL, NULL, NULL,
		THREAD_UARTPROCESS_PRIORITY, 0, 0);
K_THREAD_DEFINE(thread_cellrecv_id, STACKSIZE, thread_cellrecv, NULL, NULL, NULL,
		THREAD_CELLRECV_PRIORITY, 0, 0);

int main(void) {
    uart_init();
    modem_init();
    modem_network_connect();
}

void thread_uartprocess (void) {
    while (1) {
        k_sem_take(&uart_data_ready, K_FOREVER);
        uart_process_rx();
    }
}

void thread_cellrecv (void) {
    // Only try to recv if connection configured
    k_sem_take(&connection_configured, K_FOREVER);
    while (1) {
        modem_downlink_monitor();
    } 
}