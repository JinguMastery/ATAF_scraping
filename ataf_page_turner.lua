
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

    function wait_new_decision(ref_num)
        local test = 100
        local ref_num_elem = splash:select('p.soustitre a span')
        while test > 0 and (ref_num_elem == nil or ref_num_elem:text() == ref_num) do
            test = test - 1
            splash:wait(0.1)
            ref_num_elem = splash:select('p.soustitre a span')
        end
        if test == 0 then
            print("---- New decision not found")
            return ""
        else
            return ref_num_elem:text()
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
            if selector == 'a.iceCmdLnk#j_id8\\:j_id24' then
                local ref_num = splash:select('p.soustitre a span'):text()
                elem:mouse_click()
                return wait_new_decision(ref_num)
            else
                elem:mouse_click()
                return wait_page_refresh()
            end
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
    local lang = splash.args.lang
    local page = splash.args.page

    assert(select_dates_court(start_date, end_date, court))
    assert(click_btn("input[type=submit][value=rechercher].iceCmdBtn"))

    local first_ref_num = wait_and_select('a.iceCmdLnk#form\\:resultTable\\:0\\:j_id36'):text()

    while not click_btn('a#form\\:j_id63idx' .. page) do
        click_btn('a.iceCmdLnk#form\\:j_id63fastf')
        click_btn('a.iceCmdLnk#form\\:j_id63previous')
    end

    assert(click_btn('a.iceCmdLnk#form\\:resultTable\\:' .. (page-1)*10 .. '\\:j_id36'))

    local decision_pages = {}
    local decision_img_list = {}

    local lang_selector
    if lang == "FR" then
        lang_selector = 'input.iceCmdBtn#j_id8\\:j_id31'
    elseif lang == "DE" then
        lang_selector = 'input.iceCmdBtn#j_id8\\:j_id30'
    elseif lang == "IT" then
        lang_selector = 'input.iceCmdBtn#j_id8\\:j_id32'
    end
    
    local page_inc = 0
    repeat
        assert(click_btn(lang_selector))
        assert(splash:select('div.iceOutConStatActv'):styles()["visibility"] == "hidden")
        decision_pages[#decision_pages+1] = splash:html()
        --decision_img_list[#decision_img_list+1] = splash:png()
        local new_ref_num = click_btn('a.iceCmdLnk#j_id8\\:j_id24')
        page_inc = page_inc + 1
    until new_ref_num == "" or new_ref_num == first_ref_num or page_inc == 10
    
    return {
        decisions=decision_pages,
        --decision_images = decision_img_list,
        court_num=court,
        date_range=start_date .. ", " .. end_date,
        language=lang
    }

end