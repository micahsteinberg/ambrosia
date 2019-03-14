import time
import re

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

from urllib.request import Request, urlopen
from urllib.parse import urljoin
from bs4 import BeautifulSoup as soup

HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.90 Safari/537.36'}


'''
Things to do:
    - fix images
    - read rating
    - try to estimate time?
    - write to json and send in one write on button press
'''


def connect_to_db():
    cred = credentials.Certificate('ambrosia-b123f-firebase-adminsdk-k989n-22556cae05.json')
    firebase_admin.initialize_app(cred, {'projectId' : 'ambrosia-b123f'})
    db = firestore.client()
    return db.collection(u'recipes')

def write_to_db(coll, doc, data):
    coll.document(doc).set(data)

def get_recipe_urls(url):
    req = Request(url, headers=HEADERS)
    xml = urlopen(req).read()
    page_soup = soup(xml, "html.parser")

    return [url_tag.find('loc').contents[0] for url_tag in page_soup.findAll("url")]

def parse_food52_recipe(url):
    req = Request(url, headers=HEADERS)
    html = urlopen(req).read()
    page_soup = soup(html, "html.parser")
    recipe_body = page_soup.find("section", {"class" : "recipe content__container"})

    data = {"url" : url}

    name_data = recipe_body.find("h1", {"class" : "recipe__header-title"})
    if name_data:
        if name_data.contents:
            data.update(name = name_data.contents[0].strip())

    recipe_meta = recipe_body.find("div", {"class" : "recipe__meta"})
    if recipe_meta:
        ad = recipe_meta.find("div")
        if ad:
            author_data = ad.find("a")
            if author_data:
                if author_data.contents:
                    data.update(author = {"name" : author_data.contents[0], "link" : author_data["href"]})

        divs = recipe_meta.findAll("div")
        if len(divs) >= 2:
            date_data = divs[1]
            if date_data:
                if date_data.contents:
                    data.update(date = date_data.contents[0])

    recipe_data = recipe_body.find("article", {"class" : "recipe"})
    if recipe_data:
            image_frames = recipe_data.findAll("figure", {"class" : "photo-frame"})
            if image_frames:
                imgs = []
                for frame in image_frames:
                    src = frame.find("source")
                    if "data-srcset" in src:
                        imgs.append(src["data-srcset"])
                    elif "srcset" in src:
                        imgs.append(src["srcset"])
                data.update(images = imgs)

            vd = recipe_data.find("div", {"class" : "recipe__video-aspect"})
            if vd:
                video_data = vd.find("iframe")
                if video_data:
                    if "src" in video_data:
                        data.update(video = video_data["src"])

            recipe_text = str(recipe_data.find("div", {"class" : "recipe__text"}))
            if recipe_text:
                makes_idx = recipe_text.find("Makes:")
                if makes_idx != -1:
                    qnt = recipe_text[makes_idx+16:makes_idx+46].split('"')[0].strip()
                    data.update(quantity = qnt)

                tm = {}
                prep_idx = recipe_text.find("Prep time:")
                if prep_idx != -1:
                    prp = recipe_text[prep_idx+20:prep_idx+50].split('"')[0].strip()
                    tm.update(prep = prp)
                cook_idx = recipe_text.find("Cook time:")
                if cook_idx != -1:
                    ck = recipe_text[cook_idx+20:cook_idx+50].strip()
                    tm.update(cook = ck)
                if tm:
                    data.update(time = tm)

            recipe_lists = recipe_data.find("div", {"class" : "recipe-lists"})
            if recipe_lists:
                igrs = []
                rl = recipe_lists.find("ul", "recipe-list")
                if rl:
                    items = rl.findAll("li")
                    for item in items:
                        igr = {}
                        qnt = item.find("span", {"class" : "recipe-list-quantity"})
                        if qnt:
                            if qnt.contents:
                                igr.update(quantity = qnt.contents[0])

                        nm = item.find("span", {"class" : "recipe-list-item-name"})
                        if nm:
                            if nm.contents:
                                igr.update(name = nm.contents[0].strip())

                        igrs.append(igr)
                data.update(ingredients = igrs)

                dirs = []
                ol = recipe_lists.find("ol")
                if ol:
                    steps = ol.findAll("li")
                    for i, step in enumerate(steps):
                        if step.contents:
                            dirs.append({"number" : i+1, "direction" : step.contents[0].strip()})
                data.update(directions = dirs)

    return data


# MAIN CODE:
if __name__ == "__main__":

    (pageMin, pageMax) = (1, 15)

    for i in range(pageMin, pageMax+1):

        db_coll = connect_to_db()

        urls = get_recipe_urls('https://food52.com/sitemap-recipes-'+str(i)+'.xml');

        for j, url in enumerate(urls):
            try:
                data = parse_food52_recipe(url)
                write_to_db(db_coll, data["name"], data)
            except Exception as e:
                print("Exception! - {0}".format(e))

            print("Page "+str(i)+" of "+str(pageMax)+", recipe "+str(j+1)+" of "+str(len(urls))+".", end="\r")
            time.sleep(2)

    print("\nCompleted!")
