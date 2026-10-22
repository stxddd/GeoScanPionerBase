local UART_PORT = 4
local UART_BAUDRATE = 9600
local UART_STOP_BITS = 1
local LED_COUNT = 4
local TIMER_INTERVAL = 0.1
local LOW_VOLTAGE_EVENT = Ev.LOW_VOLTAGE2
local LED_LEFT = 3    
local LED_RIGHT = 0   
local DEAD_PX = 15  

local uart = Uart.new(
    UART_PORT,
    UART_BAUDRATE,
    Uart.PARITY_NONE,
    UART_STOP_BITS
)

local leds = Ledbar.new(LED_COUNT)
local get_measure_timer
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
    local data = uart:read(uart:bytesToRead()) or "0"
    if #data == 0 then
        return nil   -- в этом такте ничего не пришло: цвет не меняем
    end

    if unpack_byte ~= nil then
        local value = unpack_byte("B", data)
        return value
    end

    return 20
end

local function update_lights()
    local value = read_data()
    if value == nil then
        return   -- в этом такте ничего не пришло: ничего не меняем
    end
    -- по умолчанию оба гасим
    leds:set(LED_LEFT, 0, 0, 0)
    leds:set(LED_RIGHT, 0, 0, 0)

    if value == 0 then
        return   -- линии нет
    end

    local dx = value - 50
    if math.abs(dx) <= DEAD_PX then
        return   -- в пределах нормы: оба не горят
    end

    -- яркость: чем дальше за пределами нормы, тем ярче (от 0.1 до 1)
    local k = (math.abs(dx) - DEAD_PX) / (49 - DEAD_PX)
    if k > 1 then k = 1 end
    k = 0.1 + 0.9 * k
    if dx < 0 then
        leds:set(LED_LEFT, k, k, k)    -- линия левее -> надо влево
    elseif dx > 0 then
        leds:set(LED_RIGHT, k, k, k)   -- линия правее -> надо вправо
    end
end

get_measure_timer = Timer.new(TIMER_INTERVAL, update_lights)
set_color(0, 0, 0)   -- при старте все диоды выключены
get_measure_timer:start() 
