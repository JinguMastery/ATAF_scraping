
function main(splash)
    -- Functions with splash access

    function wait_and_select(selector)
        local test = 100
        while test > 0 and splash:select(selector) == nil do
            test = test - 1
            splash:wait(0.1)
        end
        if test == 0 then
            print("---- Not found")
            return nil
        else
            return splash:select(selector)
        end
    end

    function wait_page_refresh()
        local test = 100
        local divState = splash:select('div.iceOutConStatActv')
        while test > 0 and (divState == nil or divState:styles()["visibility"] == "visible") do
            test = test - 1
            splash:wait(0.1)
            divState = splash:select('div.iceOutConStatActv')
        end
        if test == 0 then
            print("---- Not refreshed")
            return false
        else
            return true
        end
    end

    function click_btn(selector)
        local elem = wait_and_select(selector)
        if elem ~= nil then
            elem:mouse_click()
            return wait_page_refresh()
        else
            return false
        end
    end

    function select_dates_court(start_date, end_date, court)

        assert(splash:runjs([[document.querySelector("input.iceSelInpDateInput[name$=calFrom]").value = "]] .. start_date .. '"'))
        assert(splash:runjs([[document.querySelector("input.iceSelInpDateInput[name$=calTo]").value = "]] .. end_date .. '"'))
        
        local court_str = tostring(court-1)
        local elem = splash:select("a.iceCmdLnk#form\\:tree\\:n-" .. court_str .. "\\:j_id75")
        if elem ~= nil then
            elem:mouse_click()
            return wait_page_refresh()
        else
            return false
        end
    end

    --run
    assert(splash:go(splash.args.url))
    assert(wait_and_select('input.iceSelInpDateInput'))

    local start_date = splash.args.dates[1]
    local end_date = splash.args.dates[2]
    local court = splash.args.court

    assert(select_dates_court(start_date, end_date, court))
    assert(click_btn("input[type=submit][value=rechercher].iceCmdBtn"))
    
    if wait_and_select("a[id^=form\\:j_id63idx]") == nil then
        return {}
    end

    local all_pages = splash:select_all("a[id^=form\\:j_id63idx]")
    local html_pages = {}
    local img_list = {}
    repeat
        assert(splash:select('div.iceOutConStatActv'):styles()["visibility"] == "hidden")
        html_pages[#html_pages+1] = splash:html()
        --img_list[#img_list+1] = splash:png()
    until not click_btn('a.iceCmdLnk#form\\:j_id63next')

    return {
        htmls=html_pages,
        --images=img_list,
        court_num=court,
        date_range=splash.args.dates,
        num_pages=#all_pages,
    }

end