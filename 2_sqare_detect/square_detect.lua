--   LED_SHIFT_LEFT  БЕЛЫЙ  — лента левее курса: сдвинуться влево
--   LED_SHIFT_RIGHT БЕЛЫЙ  — лента правее курса: сдвинуться вправо
--   LED_TURN_LEFT   ЖЁЛТЫЙ — камера повернула НАЛЕВО  (1.5 с)
--   LED_TURN_RIGHT  ЖЁЛТЫЙ — камера повернула НАПРАВО (1.5 с)
--   все не горят           — лента под дроном
--   крайние КРАСНЫЕ        — ленты не видно

local LED_SHIFT_LEFT = 3
local LED_TURN_LEFT = 1
local LED_TURN_RIGHT = 2
local LED_SHIFT_RIGHT = 0

local ON_PX = 15        -- смещение больше — зажечь
local OFF_PX = 8        -- смещение меньше — погасить
local TURN_TICKS = 15   -- сколько тактов (по 0.1 с) показывать поворот
local SILENCE = 15      -- тактов без данных от камеры -> "ленты нет"

local uart = Uart.new(4, 9600, Uart.PARITY_NONE, 1)
local leds = Ledbar.new(4)
local unpack_byte = string.unpack

local shift = "lost"    -- "left", "right", "center", "lost"
local dir = nil         
local turn = 0      
local turn_left = 0     
local silent = 0

local function read_data()
    local data = uart:read(uart:bytesToRead()) or ""
    if #data == 0 then
        return nil
    end
    return unpack_byte("B", data, #data)  
end

local function update()
    if turn_left > 0 then
        turn_left = turn_left - 1
        if turn_left == 0 then turn = 0 end
    end

    local value = read_data()
    if value == nil then
        silent = silent + 1
        if silent >= SILENCE then shift = "lost" end
    else
        silent = 0
        if value == 0 then
            shift = "lost"
        else
            local v = value - 1
            local d = math.floor(v / 31)                
            local cross = (v - d * 31 - 15) * 3         

            if dir ~= nil and d ~= dir then           
                if d == (dir + 1) % 4 then turn = 1 else turn = -1 end
                turn_left = TURN_TICKS
            end
            dir = d

            if shift == "lost" then shift = "center" end
            if cross < -ON_PX then shift = "left"
            elseif cross > ON_PX then shift = "right"
            elseif math.abs(cross) < OFF_PX then shift = "center"
            end
        end
    end

    if shift == "lost" then
        leds:set(LED_SHIFT_LEFT, 1, 0, 0)
        leds:set(LED_SHIFT_RIGHT, 1, 0, 0)
    else
        if shift == "left" then leds:set(LED_SHIFT_LEFT, 1, 1, 1) else leds:set(LED_SHIFT_LEFT, 0, 0, 0) end
        if shift == "right" then leds:set(LED_SHIFT_RIGHT, 1, 1, 1) else leds:set(LED_SHIFT_RIGHT, 0, 0, 0) end
    end
    if turn == -1 then leds:set(LED_TURN_LEFT, 1, 0.8, 0) else leds:set(LED_TURN_LEFT, 0, 0, 0) end
    if turn == 1 then leds:set(LED_TURN_RIGHT, 1, 0.8, 0) else leds:set(LED_TURN_RIGHT, 0, 0, 0) end
end

function callback(event)
end

squareTimer = Timer.new(0.1, function () update() end)
squareTimer:start()
