
-
-- Pioneer Base + OPT
-- Взлёт, ожидание 10 секунд, посадка

function callback(event)
    if event == Ev.TAKEOFF_COMPLETE then
        -- Взлёт завершён
        -- Ожидаем 10 секунд
        Timer.callLater(10, function()
            ap.push(Ev.MCE_LANDING)
        end)
    end
end

-- Предполётная подготовка
ap.push(Ev.MCE_PREFLIGHT)

-- Команда взлёта через 6 секунд
Timer.callLater(6, function()
    ap.push(Ev.MCE_TAKEOFF)
end)

-- Pioneer Base + OPT
-- Взлёт, ожидание 10 секунд, посадка

function callback(event)
    if event == Ev.TAKEOFF_COMPLETE then
        -- Взлёт завершён
        -- Ожидаем 10 секунд
        Timer.callLater(10, function()
            ap.push(Ev.MCE_LANDING)
        end)
    end
end

-- Предполётная подготовка
ap.push(Ev.MCE_PREFLIGHT)

-- Команда взлёта через 6 секунд
Timer.callLater(6, function()
    ap.push(Ev.MCE_TAKEOFF)
end)

-- Pioneer Base + OPT
-- Взлёт, ожидание 10 секунд, посадка

function callback(event)
    if event == Ev.TAKEOFF_COMPLETE then
        -- Взлёт завершён
        -- Ожидаем 10 секунд
        Timer.callLater(10, function()
            ap.push(Ev.MCE_LANDING)
        end)
    end
end

-- Предполётная подготовка
ap.push(Ev.MCE_PREFLIGHT)

-- Команда взлёта через 6 секунд
Timer.callLater(6, function()
    ap.push(Ev.MCE_TAKEOFF)
end)

-- Pioneer Base + OPT
-- Взлёт, ожидание 10 секунд, посадка

function callback(event)
    if event == Ev.TAKEOFF_COMPLETE then
        -- Взлёт завершён
        -- Ожидаем 10 секунд
        Timer.callLater(10, function()
            ap.push(Ev.MCE_LANDING)
        end)
    end
end

-- Предполётная подготовка
ap.push(Ev.MCE_PREFLIGHT)

-- Команда взлёта через 6 секунд
Timer.callLater(6, function()
    ap.push(Ev.MCE_TAKEOFF)
end)
- Pioneer Base + OPT
-- Взлёт, ожидание 10 секунд, посадка

function callback(event)
    if event == Ev.TAKEOFF_COMPLETE then
        -- Взлёт завершён
        -- Ожидаем 10 секунд
        Timer.callLater(10, function()
            ap.push(Ev.MCE_LANDING)
        end)
    end
end

-- Предполётная подготовка
ap.push(Ev.MCE_PREFLIGHT)

-- Команда взлёта через 6 секунд
Timer.callLater(6, function()
    ap.push(Ev.MCE_TAKEOFF)
end)

