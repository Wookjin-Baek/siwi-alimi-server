#server.py
#runs the flask server, includes app_current_status and app_future_status

from flask import Flask, json, request, jsonify
import requests
import sys
import re
from tabnanny import check
import time
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup as Soup

app = Flask(__name__)

def initializeChromeOption():
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument('window-size=1920x1080')
    options.add_argument("disable-gpu")

    return options

def mountChromeBrowser(options=None):
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    return driver

def generateChecklistCurrent(date=None, type=None, location=None, restriction=None, alternative=None, detail=None):
    checklist = []
    if date is not None: checklist.append(0)
    if type is not None: checklist.append(1)
    if location is not None: checklist.append(2)
    if restriction is not None: checklist.append(3)
    if alternative is not None: checklist.append(4)
    if detail is not None: checklist.append(5)
    
    return checklist

def generateChecklistFuture(date=None, type=None, restriction=None, location=None, detail=None):
    checklist = []
    if date is not None: checklist.append(0)
    if type is not None: checklist.append(1)
    if restriction is not None: checklist.append(2)
    if location is not None: checklist.append(3)
    if detail is not None: checklist.append(4)
    
    return checklist

def parseWebSite(driver=None, url=None):
    driver.get(url)
    driver.implicitly_wait(3)

    html = driver.page_source
    soup = Soup(html, 'html.parser')

    return soup

def getNewInfo(soup=None, checklist=None, date=None, type=None, location=None, restriction=None, alternative=None, detail=None, flag='current'):
    raw_information = soup.find_all('td', 'last')
    sub_length = 6 if flag == 'current' else 5 if flag == 'future' else None
    main_length = int(len(raw_information)/sub_length)

    for index in range(0, main_length):
        for subIndex in range(0, sub_length):
            if subIndex in checklist:
                str_information = str(raw_information[int(index*sub_length+subIndex)])
                formatStart = [m.start() for m in re.finditer('<', str_information)]
                formatEnd = [m.start() for m in re.finditer('>', str_information)]
                str_information = preprocessRaw(str_information=str_information, formatStart=formatStart, formatEnd=formatEnd)
                if flag == 'current':
                    if subIndex == 0: date.append(str_information)
                    elif subIndex == 1: type.append(str_information)
                    elif subIndex == 2: location.append(str_information)
                    elif subIndex == 3: restriction.append(str_information)
                    elif subIndex == 4: alternative.append(str_information)
                    elif subIndex == 5: detail.append(str_information.replace('\n', ' '))
                elif flag == 'future':
                    if subIndex == 0: date.append(str_information)
                    elif subIndex == 1: type.append(str_information)
                    elif subIndex == 2: restriction.append(str_information)
                    elif subIndex == 3: location.append(str_information)
                    elif subIndex == 4: detail.append(str_information.replace('\n', ' '))
            else:
                pass

    return date, type, location, restriction, alternative, detail

def preprocessRaw(str_information=None, formatStart=None, formatEnd=None):
    for formatIndex in range(0, len(formatStart)):
        str_information = str_information.replace(str_information[formatStart[formatIndex]:formatEnd[formatIndex]+1], '', 1)
        for formatUpdate in range(formatIndex+1, len(formatStart)):
            formatStart[formatUpdate] -= formatEnd[formatIndex] - formatStart[formatIndex] + 1
            formatEnd[formatUpdate] -= formatEnd[formatIndex] - formatStart[formatIndex] + 1
    
    return str_information

def prepareNextParsing(secs=60, date=None, type=None, location=None, restriction=None, alternative=None, detail=None):
    time.sleep(secs)
    if date is not None: date.clear()
    if type is not None: type.clear()
    if location is not None: location.clear()
    if restriction is not None: restriction.clear()
    if alternative is not None: alternative.clear()
    if detail is not None: detail.clear()

    return date, type, location, restriction, alternative, detail

def extractTypeEvent(keyword=None, type=None):
    event_list = []
    for index in range(0, len(type)):
        if type[index].find(keyword) != -1:
            event_list.append(index)
    
    return event_list

def compareTwoDetail(detail1=None, detail2=None, event_list=None):
    compare_list = []
    for index in event_list:
        for subIndex in range(0, len(detail2)):
            if detail2[subIndex] == detail1[index]:
                compare_list.append(subIndex)

    return compare_list


###### current and future protest and event


@app.route('/current_protest_and_event', methods = ['POST'])
def current_protest_and_event():

    url_current = 'https://topis.seoul.go.kr/map/openAccMap.do'

    type_list = ['집회및행사', '공사', '차량고장', '교통사고'] # add restriction types as many as possible
    date, type, location, restriction, alternative, detail = [], [], None, [], None, [] # create lists for the information
    checklist_current = generateChecklistCurrent(date=date, type=type, restriction=restriction, detail=detail)

    options = initializeChromeOption()
    driver = mountChromeBrowser(options=options)

    soup_current = parseWebSite(driver=driver, url=url_current)
    date, type, location, restriction, alternative, detail =  getNewInfo(soup=soup_current, checklist=checklist_current, date=date, type=type, restriction=restriction, detail=detail)
    event_list = extractTypeEvent(type_list[0], type)
        
    result = ""
    count = 1
    for index in event_list:
        result += f'{count}. 기간: {date[index]}\n'
        result += f'유형/통제: {type[index]}/{restriction[index]}\n'
        result += f'세부 사항: {detail[index]}'
        count += 1
    
    if not result:
        answer = {
            "version" : "2.0",
            "template" : {
                "outputs" : [
                    {
                        "simpleText" : {
                            "text" : "현재 집회 및 행사가 없습니다."
                        }
                    }
                ]
            }
        }
    else:    
        answer = {
            "version" : "2.0",
            "template" : {
                "outputs" : [
                    {
                        "simpleText" : {
                            "text" : "현재 집회 및 행사 목록입니다." + "\n" + result
                        }
                    }
                ]
            }
        }
    
    return jsonify(answer)


@app.route('/future_protest_and_event', methods = ['POST'])
def future_protest_and_event():

    url_current = 'https://topis.seoul.go.kr/map/openAccMap.do'
    url_future = 'https://topis.seoul.go.kr/map/openControlMap.do'

    type_list = ['집회및행사', '공사', '차량고장', '교통사고'] # add restriction types as many as possible
    date, type, location, restriction, alternative, detail = [], [], None, [], None, [] # create lists for the information
    date_next, type_next, restriction_next, location_next, detail_next = [], [], [], None, []
    checklist_current = generateChecklistCurrent(date=date, type=type, restriction=restriction, detail=detail)
    checklist_future = generateChecklistFuture(date=date_next, type=type_next, restriction=restriction_next, detail=detail_next)

    options = initializeChromeOption()
    driver = mountChromeBrowser(options=options)

    soup_current = parseWebSite(driver=driver, url=url_current)
    date, type, location, restriction, alternative, detail =  getNewInfo(soup=soup_current, checklist=checklist_current, date=date, type=type, restriction=restriction, detail=detail, flag='current')
    event_list = extractTypeEvent(type_list[0], type)
        
    soup_future = parseWebSite(driver=driver, url=url_future)
    date_next, type_next, location_next, restriction_next, alternative_next, detail_next =  getNewInfo(soup=soup_future, checklist=checklist_future, date=date_next, type=type_next, restriction=restriction_next, detail=detail_next, flag='future')
    compare_list = compareTwoDetail(detail1=detail, detail2=detail_next, event_list=event_list)

    result = ""
    count = 1
    for index in range(0, len(date_next)):
        if index not in compare_list:
            result += f'{count}. 기간: {date_next[index]}\n'
            result += f'유형/통제: {type_next[index]}/{restriction_next[index]}\n'
            result += f'세부 사항: {detail_next[index]}\n'
            count += 1


    if not result:
        answer = {
            "version" : "2.0",
            "template" : {
                "outputs" : [
                    {
                        "simpleText" : {
                            "text" : "예정 집회 및 행사가 없습니다."
                        }
                    }
                ]
            }
        }
    else:    
        answer = {
            "version" : "2.0",
            "template" : {
                "outputs" : [
                    {
                        "simpleText" : {
                            "text" : "예정 집회 및 행사 목록입니다." + "\n" + result
                        }
                    }
                ]
            }
        }
    
    return jsonify(answer)




#### current and future protest ####


@app.route('/current_protest', methods = ['POST'])
def current_protest():

    url_current = 'https://topis.seoul.go.kr/map/openAccMap.do'

    type_list = ['집회및행사(집회/시위)', '집회및행사(행사)', '공사', '차량고장', '교통사고'] # add restriction types as many as possible
    date, type, location, restriction, alternative, detail = [], [], None, [], None, [] # create lists for the information
    checklist_current = generateChecklistCurrent(date=date, type=type, restriction=restriction, detail=detail)

    options = initializeChromeOption()
    driver = mountChromeBrowser(options=options)

    soup_current = parseWebSite(driver=driver, url=url_current)
    date, type, location, restriction, alternative, detail =  getNewInfo(soup=soup_current, checklist=checklist_current, date=date, type=type, restriction=restriction, detail=detail)
    event_list = extractTypeEvent(type_list[0], type)
        
    result = ""
    count = 1
    for index in event_list:
        result += f'{count}. 기간: {date[index]}\n'
        result += f'유형/통제: {type[index]}/{restriction[index]}\n'
        result += f'세부 사항: {detail[index]}'
        count += 1
    

    if not result:
        answer = {
            "version" : "2.0",
            "template" : {
                "outputs" : [
                    {
                        "simpleText" : {
                            "text" : "현재 집회 및 시위가 없습니다."
                        }
                    }
                ]
            }
        }
    
    else:    
        answer = {
            "version" : "2.0",
            "template" : {
                "outputs" : [
                    {
                        "simpleText" : {
                            "text" : "현재 집회 및 시위 목록입니다." + "\n" + result
                        }
                    }
                ]
            }   
        }   
    
    return jsonify(answer)


@app.route('/future_protest', methods = ['POST'])
def future_protest():

    def get_url_for_protest():
        days = ['월', '화', '수', '목', '금', '토', '일']
        today_month = datetime.datetime.now().month
        today_day = datetime.datetime.now().day
        a = datetime.datetime.today().weekday()
        today_weekday = days[a]

        search_key = str(today_month) + '월 ' + str(today_day) + '일 ' + '(' + (today_weekday) + ') ' + "집회 및 행사"

        options = initializeChromeOption()
        driver = mountChromeBrowser(options=options)

        driver.get('https://www.spatic.go.kr/article/list.do?boardId=4&currentPageNo=1&menuId=21&recordCountPerPage=10&searchEtc1=&searchEtc2=&searchEtc3=&searchEtc4=&searchEtc5=&searchSelect=title&searchValue=')

        searchbox = driver.find_element(By. CSS_SELECTOR, '#searchValue')
        searchbox.send_keys(search_key)

        searchbutton = driver.find_element(By. CSS_SELECTOR, '#searchForm > a')
        searchbutton.click()

        result_url = driver.find_element(By. CSS_SELECTOR, '#contents > div.board_body > table > tbody > tr > td.board_list_title > a').get_attribute('href')

        driver.close()
        return(result_url)

    #css selector for search box input : #searchValue
    #css selector for href of search result : #contents > div.board_body > table > tbody > tr > td.board_list_title > a

    def get_future_protest():
        try:
            response = requests.get(str(get_url_for_protest()))

            if response.status_code == 200:
                html = response.text
                soup = Soup(html, 'html.parser')

                future_protest = ""

                for i in range(2, 15):
                    try:
                        protest_place = '#contents > div.board_body > table > tbody > tr.content_area > td > table > tbody > tr:nth-child' + '(' + str(i) + ')'
                        content = soup.select_one(protest_place)
                        content_text = content.get_text()
                        future_protest += content_text[:1] + ". " + content_text[1:] + "\n"
                    except:
                        pass
                return(future_protest)

            else : 
                return(response.status_code)
        
        except:
            return("아직 오늘의 집회 정보가 업로드되지 않았습니다.")


#css selector for "n"th protest content: 
#contents > div.board_body > table > tbody > tr.content_area > td > table > tbody > tr:nth-child(2) > td:nth-child("n")


    answer = {
        "version" : "2.0",
        "template" : {
            "outputs" : [
                {
                    "simpleText" : {
                        "text" : str(datetime.datetime.now().date()) + "의 예정 집회 및 시위 목록입니다." + "\n" + get_future_protest()
                    }
                }
            ]
        }
    }
    
    return jsonify(answer)




#### current and future event #####

@app.route('/current_event', methods = ['POST'])
def current_event():

    url_current = 'https://topis.seoul.go.kr/map/openAccMap.do'

    type_list = ['집회및행사(집회/시위)', '집회및행사(행사)', '공사', '차량고장', '교통사고'] # add restriction types as many as possible
    date, type, location, restriction, alternative, detail = [], [], None, [], None, [] # create lists for the information
    checklist_current = generateChecklistCurrent(date=date, type=type, restriction=restriction, detail=detail)

    options = initializeChromeOption()
    driver = mountChromeBrowser(options=options)

    soup_current = parseWebSite(driver=driver, url=url_current)
    date, type, location, restriction, alternative, detail =  getNewInfo(soup=soup_current, checklist=checklist_current, date=date, type=type, restriction=restriction, detail=detail)
    event_list = extractTypeEvent(type_list[1], type)
        
    result = ""
    count = 1
    for index in event_list:
        result += f'{count}. 기간: {date[index]}\n'
        result += f'유형/통제: {type[index]}/{restriction[index]}\n'
        result += f'세부 사항: {detail[index]}'
        count += 1
    

    if not result:
        answer = {
            "version" : "2.0",
            "template" : {
                "outputs" : [
                    {
                        "simpleText" : {
                            "text" : "현재 행사가 없습니다."
                        }
                    }
                ]
            }
        }
    
    else:    
        answer = {
            "version" : "2.0",
            "template" : {
                "outputs" : [
                    {
                        "simpleText" : {
                            "text" : "현재 행사 목록입니다." + "\n" + result
                        }
                    }
                ]
            }   
        }
    
    return jsonify(answer)



@app.route('/future_event', methods = ['POST'])
def future_event():

    url_current = 'https://topis.seoul.go.kr/map/openAccMap.do'
    url_future = 'https://topis.seoul.go.kr/map/openControlMap.do'

    type_list = ['집회및행사(집회/시위)', '집회및행사(행사)', '공사', '차량고장', '교통사고'] # add restriction types as many as possible
    date, type, location, restriction, alternative, detail = [], [], None, [], None, [] # create lists for the information
    date_next, type_next, restriction_next, location_next, detail_next = [], [], [], None, []
    checklist_current = generateChecklistCurrent(date=date, type=type, restriction=restriction, detail=detail)
    checklist_future = generateChecklistFuture(date=date_next, type=type_next, restriction=restriction_next, detail=detail_next)

    options = initializeChromeOption()
    driver = mountChromeBrowser(options=options)

    soup_current = parseWebSite(driver=driver, url=url_current)
    date, type, location, restriction, alternative, detail =  getNewInfo(soup=soup_current, checklist=checklist_current, date=date, type=type, restriction=restriction, detail=detail, flag='current')
    event_list = extractTypeEvent(type_list[1], type)
        
    soup_future = parseWebSite(driver=driver, url=url_future)
    date_next, type_next, location_next, restriction_next, alternative_next, detail_next =  getNewInfo(soup=soup_future, checklist=checklist_future, date=date_next, type=type_next, restriction=restriction_next, detail=detail_next, flag='future')
    compare_list = compareTwoDetail(detail1=detail, detail2=detail_next, event_list=event_list)

    result = ""
    count = 1
    for index in range(0, len(date_next)):
        if index not in compare_list:
            result += f'{count}. 기간: {date_next[index]}\n'
            result += f'유형/통제: {type_next[index]}/{restriction_next[index]}\n'
            result += f'세부 사항: {detail_next[index]}\n'
            count += 1

    
    if not result:
        answer = {
            "version" : "2.0",
            "template" : {
                "outputs" : [
                    {
                        "simpleText" : {
                            "text" : "예정 행사가 없습니다."
                        }
                    }
                ]
            }
        }
    
    else:    
        answer = {
            "version" : "2.0",
            "template" : {
                "outputs" : [
                    {
                        "simpleText" : {
                            "text" : "예정 행사 목록입니다." + "\n" + result
                        }
                    }
                ]
            }   
        }
    
    return jsonify(answer)






@app.route('/keyboard')
def Keyboard():
    dataSend = {
    "Subject":"OSSP",
    "user":"siwi_chatbot"
    }
    return jsonify(dataSend)


if __name__ == "__main__":
    app.run(host = '0.0.0.0', port = 5000)