cmake_minimum_required(VERSION 3.12)

# build for the Raspberry Pi Debug Probe by default
set(PICO_BOARD debug_probe CACHE STRING "Board type")

set(CMAKE_BUILD_TYPE RelWithDebInfo)

include(pico_sdk_import.cmake)

set(FREERTOS_KERNEL_PATH ${CMAKE_CURRENT_LIST_DIR}/freertos)
include(FreeRTOS_Kernel_import.cmake)

project(debugprobe)

pico_sdk_init()

add_executable(debugprobe
        src/probe_config.c
        src/main.c
        src/usb_descriptors.c
        src/probe.c
        src/cdc_uart.c
        src/get_serial.c
        src/sw_dp_pio.c
        src/tusb_edpt_handler.c
        src/autobaud.c
)

target_sources(debugprobe PRIVATE
        CMSIS_DAP/CMSIS/DAP/Firmware/Source/DAP.c
        CMSIS_DAP/CMSIS/DAP/Firmware/Source/JTAG_DP.c
        CMSIS_DAP/CMSIS/DAP/Firmware/Source/DAP_vendor.c
        CMSIS_DAP/CMSIS/DAP/Firmware/Source/SWO.c
        #CMSIS_DAP/CMSIS/DAP/Firmware/Source/SW_DP.c
        )

target_include_directories(debugprobe PRIVATE
        CMSIS_DAP/CMSIS/DAP/Firmware/Include/
        CMSIS_DAP/CMSIS/Core/Include/
        include/
        )

target_compile_options(debugprobe PRIVATE -Wall)

pico_generate_pio_header(debugprobe ${CMAKE_CURRENT_LIST_DIR}/src/probe.pio)
pico_generate_pio_header(debugprobe ${CMAKE_CURRENT_LIST_DIR}/src/probe_oen.pio)
pico_generate_pio_header(debugprobe ${CMAKE_CURRENT_LIST_DIR}/src/autobaud.pio)

# Single-wire UART for the Raspberry Pi Debug Probe: transmit open-drain on GPIO6, which shares the RX pin of the UART connector
# with the receiver (GPIO5), so one wire carries both directions. The TX pin (GPIO4) becomes an open-drain reset output for the target's
# NRST: pulled low while the host holds a CDC break, released otherwise.
option(PROBE_UART_SINGLE_WIRE "Single-wire half-duplex UART on the RX pin, reset output on the TX pin" OFF)
if (PROBE_UART_SINGLE_WIRE)
    if (NOT PICO_BOARD STREQUAL "debug_probe")
        message(FATAL_ERROR "PROBE_UART_SINGLE_WIRE needs PICO_BOARD debug_probe (it uses GPIO6, wired to the UART RX pin)")
    endif ()
    pico_generate_pio_header(debugprobe ${CMAKE_CURRENT_LIST_DIR}/src/uart_tx_od.pio)
    target_compile_definitions(debugprobe PRIVATE PROBE_UART_SINGLE_WIRE PROBE_UART_SINGLE_WIRE_PIN=6)
    set_target_properties(debugprobe PROPERTIES OUTPUT_NAME "debugprobe_single_wire")
endif ()

target_include_directories(debugprobe PRIVATE src)

# add version
add_custom_target(version
        ${CMAKE_SOURCE_DIR}/get-version.sh
        WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
)

target_include_directories(debugprobe PRIVATE
        ${CMAKE_BINARY_DIR}/generated
        )

add_dependencies(debugprobe version)

target_compile_definitions (debugprobe PRIVATE
	PICO_RP2040_USB_DEVICE_ENUMERATION_FIX=1
    PICO_ENABLE_USB_RESET_VIA_VENDOR_INTERFACE=1
)

if (NOT PICO_BOARD STREQUAL "debug_probe")
    set_target_properties(debugprobe PROPERTIES
        OUTPUT_NAME "debugprobe_on_${PICO_BOARD}"
    )
endif ()

target_link_libraries(debugprobe PRIVATE
        pico_multicore
        pico_stdlib
        pico_usb_reset
        pico_unique_id
        tinyusb_device
        tinyusb_board
        hardware_pio
        hardware_dma
        hardware_irq
        hardware_clocks
        FreeRTOS-Kernel
        FreeRTOS-Kernel-Heap1
)

pico_set_binary_type(debugprobe copy_to_ram)

pico_add_extra_outputs(debugprobe)
