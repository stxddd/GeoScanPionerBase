-- Geoscan Pioneer Base + OPT
-- Квадрат 50 x 50 см
-- Высота 0.5 м

local points = {
    {0.0, 0.5, 0.5},
    {0.5, 0.5, 0.5},
    {0.5, 0.0, 0.5},
    {0.0, 0.0, 0.5}
}

local point = 0
local finished = false

local function nextPoint()
    if finished then
        return
    end

    point = point + 1

    if point <= #points then

        local p = points[point]

        ap.goToLocalPoint(
            p[1],
            p[2],
            p[3]
        )

    else
        finished = true
        ap.push(Ev.MCE_LANDING)
    end
end


function callback(event)
    if event == Ev.TAKEOFF_COMPLETE then
        nextPoint()

    elseif event == Ev.POINT_REACHED then
        if point > 0 and not finished then
            nextPoint()
        end

    elseif event == Ev.COPTER_LANDED then
        finished = true
        
        end
end

Timer.callLater(2, function()
    ap.push(Ev.MCE_PREFLIGHT)
end)

Timer.callLater(6, function()
    ap.push(Ev.MCE_TAKEOFF)
end)

