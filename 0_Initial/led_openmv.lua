local UART_PORT = 4
local UART_BAUDRATE = 9600
local UART_STOP_BITS = 1
local LED_COUNT = 4
local DATA_STEPS = 10
local TIMER_INTERVAL = 0.1
local LOW_VOLTAGE_EVENT = Ev.LOW_VOLTAGE2

local uart = Uart.new(
    UART_PORT,
    UART_BAUDRATE,
    Uart.PARITY_NONE,
    UART_STOP_BITS
)

local leds = Ledbar.new(LED_COUNT)
local get_measure_timer
local data_index = 7
local unpack_byte = string.unpack

local function set_color(red, green, blue)
    for index = 0, LED_COUNT - 1 do
        leds:set(index, red, green, blue)
    end
end

local function stop_on_low_voltage()
    get_measure_timer:stop()
    Timer.callLater(1, function()
        set_color(1, 0, 0)
    end)
end

function callback(event)
    if event == LOW_VOLTAGE_EVENT then
        stop_on_low_voltage()
    end
end

local function read_data()
    data_index = data_index + 1
    if data_index == DATA_STEPS + 1 then
        data_index = 0
    end

    local data = uart:read(uart:bytesToRead()) or "0"
    if #data == 0 then
        data = "\0"
    end

    leds:set(
        1,
        0,
        data_index / DATA_STEPS,
        0.5 - 0.5 * data_index / DATA_STEPS
    )

    if unpack_byte ~= nil then
        local value = unpack_byte("B", data)
        return value
    end

    return 20
end

local function update_lights()
    local intensity = read_data() / 100.0
    set_color(intensity, intensity, intensity)
end

get_measure_timer = Timer.new(TIMER_INTERVAL, update_lights)
get_measure_timer:start()
set_color(1, 0.2, 0)
