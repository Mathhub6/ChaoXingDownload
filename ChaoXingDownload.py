import json
import os
import re
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait



# 设置学习通登录信息
username = input("请输入学习通用户名：")
password = input("请输入学习通密码：")




DOWNLOAD_PATH =os.path.abspath( "./Mooc/release")
chrome_path = os.path.abspath('./chrome-win64/chrome.exe')
chromedriver_path = os.path.abspath('./chromedriver-win64/chromedriver.exe')
DATA_PATH = os.path.abspath('./User Data')
CACHE_PATH = os.path.abspath('./Cache')
prefs = {
    'download.default_directory': DOWNLOAD_PATH,  # 设置默认下载路径
    "profile.default_content_setting_values.automatic_downloads": 1  # 允许多文件下载
}


# 初始化 Selenium WebDriver
chrome_options = Options()
chrome_options.binary_location = chrome_path

chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=800,600")
chrome_options.add_argument("--disk-cache-dir=%s" % CACHE_PATH)
chrome_options.add_argument("--user-data-dir=%s" % DATA_PATH)
chrome_options.add_experimental_option("prefs", prefs)
# chrome_options.add_argument("--incognito")  # 无痕模式
# chrome_options.add_argument("--auto-open-devtools-for-tabs")

service = Service(executable_path=chromedriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)
wait = WebDriverWait(driver, 30)  # 增加等待时间

def login(username, password):
    """登录到学习通"""
    login_url = 'https://passport2.chaoxing.com/login?fid=&newversion=true&refer=https%3A%2F%2Fi.chaoxing.com'
    driver.get(login_url)
    wait.until(EC.presence_of_element_located((By.ID, 'phone'))).send_keys(username)
    wait.until(EC.presence_of_element_located((By.ID, 'pwd'))).send_keys(password)
    wait.until(EC.element_to_be_clickable((By.ID, 'loginBtn'))).click()

    try:
        wait.until(EC.presence_of_element_located((By.XPATH, "//li[contains(text(), '退出空间')]")))
        print("登录成功")
    except Exception:
        print("登录失败，请检查用户名和密码")
        driver.quit()
        exit()

def get_course_list():
    """获取课程列表"""
    course_list_url = 'https://mooc2-ans.chaoxing.com/mooc2-ans/visit/interaction'
    driver.get(course_list_url)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'course-info')))
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    courses = []
    for course_element in soup.find_all('div', class_='course-info'):
        link_element = course_element.find('a', class_='color1')
        if link_element:
            course_name = link_element.find('span', class_='course-name').text.strip()
            course_href = link_element['href']
            course_id_match = re.search(r'courseid=(\d+)', course_href)
            if course_id_match:
                courses.append({
                    'name': course_name,
                    'id': course_id_match.group(1),
                    'href': course_href
                })
    return courses

def get_course_content(course_link, course_id):
    """获取课程内容"""
    driver.get(course_link)
    chapter_link = wait.until(EC.presence_of_element_located(
        (By.XPATH, '//a[@title="章节" and @data-url="/mooc2-ans/mycourse/studentcourse"]')))
    chapter_link.click()

    new_url = re.sub(r'/mooc2-ans/mycourse/stu', '/mooc2-ans/mycourse/studentcourse', driver.current_url)
    driver.get(new_url)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'chapter_unit')))
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    content = []
    for unit in soup.find_all('div', class_='chapter_unit'):
        chapter_title = unit.find('div', class_='catalog_name').find('a', class_='clicktitle').get_text(strip=True)
        sections = [
            {
                'title': section.find('a', class_='clicktitle').text.strip(),
                'id': section.find('div', class_='chapter_item')['id'].replace('cur', ''),
                'link': f"https://mooc1.chaoxing.com/mycourse/studentstudy?chapterId={section.find('div', class_='chapter_item')['id'].replace('cur', '')}&courseId={course_id}&clazzid=82268686&cpi=207357565&enc=17e478983a375dc5d27b9c2161e3a0d1&mooc2=1&openc=0fd608d5ef54aa63d5b90ed324a6be77"
            }
            for section in unit.find_all('li')
        ]
        content.append({'title': chapter_title, 'sections': sections})
    return content

def replace_protocol(url):
    """替换协议头"""
    return 'https://' + url[7:] if url.startswith('http://') else url

def download_course_files(course_content, courseid):
    """下载课程文件"""
    for chapter in course_content:
        for section in chapter['sections']:
            section_id = section['id']
            section_url = f'https://mooc1.chaoxing.com/mooc-ans/knowledge/cards?courseid={courseid}&knowledgeid={section_id}'
            driver.get(section_url)
            check_and_add_download_buttons(driver)
            time.sleep(5)

def check_and_add_download_buttons(driver):
    """检查并添加下载按钮"""
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    iframes = soup.find_all('div', class_='ans-attach-ct')
    for iframe in iframes:
        inner_iframe = iframe.find('iframe')
        data = inner_iframe.get('data')
        if data:
            # if data['type'] in [".ppt", ".pptx", ".mp4", ".pdf", ".flv", ".doc", ".docx", ".avi", ".wmv", ".mpg", ".mpeg"]:

            jsondata = json.loads(data)


            if 'objectid' in jsondata.keys():
                if jsondata["type"] in [".ppt", ".pptx", ".pdf", ".doc", ".docx"]:
                    objectid = jsondata['objectid']
                    url = f"https://mooc1-1.chaoxing.com/ananas/status/{objectid}?flag=normal"
                    driver.execute_script(f'''
                        var e = document.createElement('a');
                        e.href = "{url}";
                        e.target = '_self';
                        document.body.appendChild(e);
                        e.click();
                        document.body.removeChild(e);
                    ''')
                    download_data = json.loads(BeautifulSoup(driver.page_source, 'html.parser').find('pre').text)
                    download_url = replace_protocol(download_data['download'])
                    driver.execute_script(f'''
                        var e = document.createElement('a');
                        e.href = "{download_url}";
                        e.target = '_self';
                        document.body.appendChild(e);
                        e.click();
                    document.body.removeChild(e);
                    ''')
                    print(f"{download_data['filename']}下载中...")

def display_course_tree(course_content):
    """显示课程内容树"""
    for chapter in course_content:
        print(f"章节: {chapter['title']}")
        for section in chapter['sections']:
            print(f"  节: {section['title']}")

def main():
    """主函数"""
    login(username,password)
    courses = get_course_list()
    for i, course in enumerate(courses):
        print(f"{i}. {course['name']} (ID: {course['id']})")
    course_index = int(input("请选择课程编号："))
    selected_course = courses[course_index]
    courseid = selected_course['id']
    course_content = get_course_content(selected_course['href'], courseid)
    display_course_tree(course_content)
    download_course_files(course_content, courseid)
    driver.quit()

if __name__ == '__main__':
    main()
