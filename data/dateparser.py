from bs4 import BeautifulSoup as Bs


async def parse(session, url: str):
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:36.0) Gecko/20100101 Firefox/36.0"
    }
    try:
        async with session.get(url=url, headers=headers) as rs:
            if rs.ok:
                response_text = await rs.text()
                soup = Bs(response_text, "lxml")
                title_name = soup.find("div", class_="anime-title").find("h1").text
                dd = soup.find("dd", class_="col-12 col-sm-8 mb-1")
                if dd is not None:
                    data = dd.find('span', class_='b-tooltipped')
                    date1 = data.text.strip()
                    date2 = data.get('data-title').strip()
                    info = dd.find('span', class_='d-none d-sm-inline').text.strip()
                    data = f"{date1} ({date2}) {info}"
                    return title_name, data
                else:
                    return
            else:
                return 
    except Exception:
        return
