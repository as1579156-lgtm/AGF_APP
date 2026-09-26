import flet as ft
import json
from pathlib import Path
import urllib.request
from urllib.parse import urljoin, quote
from html.parser import HTMLParser
import asyncio
from datetime import date
try:
    from winotify import Notification
except ImportError:
    Notification = None
import xml.etree.ElementTree as ET
import webbrowser
import sys
import unicodedata
    
# ==============================
# AGF 연도 자동화
# ==============================

CURRENT_YEAR = date.today().year
AGF_TITLE = f"AGF {CURRENT_YEAR}"
# 참가사 정보
participants = [
    {"name": "참가사 A", "booth": "B-01"},
    {"name": "참가사 B", "booth": "B-02"},
    {"name": "참가사 C", "booth": "B-03"},
]

# 배치도 파일
map_file = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / f"agf_{CURRENT_YEAR}_booth_map.png"
)

class NewsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.news = []
        self.current_link = None
        self.current_text = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs = dict(attrs)
            href = attrs.get("href", "")

            if "/post/1/" in href:
                self.current_link = href
                self.current_text = []

    def handle_data(self, data):
        if self.current_link is not None:
            text = data.strip()
            if text:
                self.current_text.append(text)

    def handle_endtag(self, tag):
        if tag == "a" and self.current_link is not None:
            title = " ".join(self.current_text).strip()

            if title:
                self.news.append({
                    "title": title,
                    "url": self.current_link,
                })

            self.current_link = None
            self.current_text = []


def fetch_agf_news():
    url = "https://www.agfkorea.com/customer?idx=1"

    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
        )

        with urllib.request.urlopen(request, timeout=10) as response:
            html = response.read().decode(
                "utf-8",
                errors="ignore",
            )

        parser = NewsParser()
        parser.feed(html)

        return parser.news

    except Exception as e:
        print("뉴스 불러오기 실패:", e)
        return []
def fetch_sns_news():
    news_items = []

    sources = [
        {
            "name": "X",
            "query": "AGF_Korea AGF 2026",
        },
        {
            "name": "Instagram",
            "query": "AGF Korea Instagram 2026",
        },
    ]

    for source in sources:
        try:
            rss_url = (
                "https://news.google.com/rss/search?"
                f"q={quote(source['query'])}"
                "&hl=ko&gl=KR&ceid=KR:ko"
            )

            request = urllib.request.Request(
                rss_url,
                headers={
                    "User-Agent": "Mozilla/5.0"
                },
            )

            with urllib.request.urlopen(
                request,
                timeout=10,
            ) as response:
                xml_data = response.read()

            root = ET.fromstring(xml_data)

            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                link = item.findtext("link", "")

                if not title or not link:
                    continue

                # ==============================
                # 한국어 SNS 뉴스만 표시
                # 아랍어 / 일본어 / 중국어 제외
                # 영어는 AGF 관련 고정 표기만 허용
                # ==============================

                has_korean = any(
                    "\uAC00" <= char <= "\uD7A3"
                    for char in title
                )

                has_arabic = any(
                    "\u0600" <= char <= "\u06FF"
                    or "\u0750" <= char <= "\u077F"
                    or "\u08A0" <= char <= "\u08FF"
                    for char in title
                )

                has_japanese = any(
                    "\u3040" <= char <= "\u30FF"
                    for char in title
                )

                has_chinese = any(
                    "\u4E00" <= char <= "\u9FFF"
                    for char in title
                )

                # 한글이 없으면 제외
                if not has_korean:
                    continue

                # 외국어 문자 제외
                if has_arabic:
                    continue

                if has_japanese:
                    continue

                if has_chinese:
                    continue

                # 영어 단어 확인
                english_words = [
                    word.strip(".,!?()[]{}:;\"'")
                    for word in title.split()
                    if any(
                        ("A" <= char <= "Z")
                        or ("a" <= char <= "z")
                        for char in word
                    )
                ]

                allowed_english = {
                    "AGF",
                    "AGF2026",
                    "KOREA",
                }

                invalid_english = [
                    word for word in english_words
                    if word.upper() not in allowed_english
                ]

                if invalid_english:
                    continue

                    if unicodedata.category(char)[0] in ("P", "S"):
                        continue

                    invalid_language = True
                    break

                if not has_korean:
                    continue

                if invalid_language:
                    continue

                news_items.append({
                    "title": title,
                    "url": link,
                    "source": source["name"],
                })

        except Exception as e:
            print(
                f"{source['name']} 뉴스 불러오기 실패:",
                e,
            )

    return news_items

def fetch_all_news():
    all_items = []

    # 공식 AGF 뉴스
    try:
        official_items = fetch_agf_news()

        for item in official_items:
            new_item = dict(item)
            new_item["category"] = "공지"
            new_item["sub_category"] = "공지"
            all_items.append(new_item)

    except Exception:
        pass

    # X / Instagram 뉴스
    try:
        sns_items = fetch_sns_news()

        for item in sns_items:
            new_item = dict(item)
            new_item["category"] = "SNS"

            source = str(new_item.get("source", "")).lower()

            if "instagram" in source:
                new_item["sub_category"] = "Instagram"
            else:
                new_item["sub_category"] = "X"

            all_items.append(new_item)

    except Exception:
        pass

    return all_items

def main(page: ft.Page):
    is_web = sys.platform == "emscripten"

    saved = False
    news_content = None
    seen_news = []
    notifications_enabled = True
    news_initialized = False

    news_category = "전체"
    news_sub_category = "X"
    all_news_items = []

    # main.py와 같은 폴더에 저장
    save_file = Path(__file__).with_name("agf_settings.json")

    # 기존 저장값 불러오기
    if (not is_web) and save_file.exists():
        try:
            settings = json.loads(
                save_file.read_text(encoding="utf-8")
            )

            saved = settings.get("saved", False)
            seen_news = settings.get("seen_news", [])
            notifications_enabled = settings.get(
                "notifications_enabled",
                True,
            )
            news_initialized = settings.get(
                "news_initialized",
                False,
            )
        except (json.JSONDecodeError, OSError):
            saved = False
            seen_news = []
            notifications_enabled = True
            news_initialized = False

    page.title = f"{AGF_TITLE} · BETA" if is_web else AGF_TITLE
    page.bgcolor = "#FFFFFF"
    page.padding = 0

       # 설정 저장
    def save_settings():
        if is_web:
            return

        settings = {
            "saved": saved,
            "seen_news": seen_news,
            "notifications_enabled": notifications_enabled,
            "news_initialized": news_initialized,
        }
        save_file.write_text(
            json.dumps(
                settings,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    # Windows 팝업 알림
    def show_windows_notification(title, message, url=None):
        if Notification is None or sys.platform != "win32":
            return

        try:
            notification = Notification(
                  app_id=AGF_TITLE,
                  title=title,
                  msg=message,
)

            if url:
                notification.add_actions(
                    label="원문 열기",
                    launch=urljoin(
                        "https://www.agfkorea.com",
                        url,
                    ),
                )

            notification.show()

            print("Windows 알림 표시:", title)

        except Exception as e:
            print("Windows 알림 실패:", e)
    # 알림 버튼
    def notification_clicked(e):
        status = (
            "새소식 자동 확인: ON"
            if notifications_enabled
            else "새소식 자동 확인: OFF"
        )

        dialog = ft.AlertDialog(
            title=ft.Text("AGF 알림"),
            content=ft.Text(
                status + "\n\n"
                "새 공지가 올라오면 뉴스 화면에서 확인할 수 있습니다."
            ),
            actions=[
                ft.TextButton(
                    "확인",
                    on_click=lambda e: page.pop_dialog(),
                ),
            ],
        )

        page.show_dialog(dialog)
   

    # ==============================
    # AGF 행사 일정 데이터
    # ==============================

    EVENT_DATA = {
        2026: {
            "start": date(2026, 12, 4),
            "end": date(2026, 12, 6),
        },
    }

    event_info = EVENT_DATA.get(CURRENT_YEAR)

    today = date.today()

    weekday_names = [
        "월", "화", "수", "목", "금", "토", "일"
    ]

    if event_info:
        event_start = event_info["start"]
        event_end = event_info["end"]

        days_left = (event_start - today).days

        start_weekday = weekday_names[event_start.weekday()]
        end_weekday = weekday_names[event_end.weekday()]

        if days_left > 0:
            dday_text = f"D-{days_left}"
            date_text = (
                f"{CURRENT_YEAR}년 "
                f"{event_start.month}월 {event_start.day}일"
                f"({start_weekday}) 시작"
            )

        elif days_left == 0:
            dday_text = "D-DAY"
            date_text = f"오늘 {AGF_TITLE} 시작!"

        elif today <= event_end:
            dday_text = "행사 진행 중"
            date_text = (
                f"{CURRENT_YEAR}년 "
                f"{event_start.month}월 {event_start.day}일"
                f"({start_weekday}) ~ "
                f"{event_end.month}월 {event_end.day}일"
                f"({end_weekday})"
            )

        else:
            dday_text = "행사 종료"
            date_text = (
                f"{CURRENT_YEAR}년 "
                f"{event_start.month}월 {event_start.day}일"
                f"({start_weekday}) ~ "
                f"{event_end.month}월 {event_end.day}일"
                f"({end_weekday})"
            )

    else:
        dday_text = "일정 준비 중"
        date_text = f"{CURRENT_YEAR}년 AGF 행사 일정 준비 중"

    # 상단 메뉴
    async def menu_clicked(e):
        await page.show_end_drawer()

    # 상단 메뉴판
    async def drawer_changed(e):
        index = e.control.selected_index

        if index is None:
            return

        navigation.selected_index = index
        await page.close_end_drawer()

        change_page(index=index)

    # AppBar 설정
    def set_appbar(index):
        titles = {
            1: "AGF 뉴스",
            2: "스테이지",
            3: "AGF 부스",
            4: "앱 설정",
        }

        # 홈 화면
        if index == 0:
            page.appbar = ft.AppBar(
                title=ft.Column(
                    spacing=0,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(
                            AGF_TITLE,
                            size=21,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            dday_text,
                            size=17,
                            weight=ft.FontWeight.BOLD,
                            color="#666666",
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                ),
                center_title=True,
                bgcolor="#FFFFFF",
                elevation=2,
                toolbar_height=68,
                actions=[
                  ft.IconButton(
                      icon=ft.Icons.NOTIFICATIONS_OUTLINED,
                      tooltip="알림",
                      on_click=notification_clicked,
                  ),
              ft.IconButton(
                      icon=ft.Icons.MENU,
                      tooltip="메뉴",
                      on_click=menu_clicked,
                  ),
                ],
            )

        # 나머지 화면
        else:
            page.appbar = ft.AppBar(
                leading=ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    tooltip="홈으로",
                    on_click=lambda e: change_page(index=0),
                ),
                title=ft.Text(
                    titles[index],
                    size=21,
                    weight=ft.FontWeight.BOLD,
                ),
                center_title=False,
                bgcolor="#FFFFFF",
                elevation=2,
                toolbar_height=68,
                actions=[
                 ft.IconButton(
    icon=ft.Icons.NOTIFICATIONS_OUTLINED,
    tooltip="알림",
    on_click=notification_clicked,
),
ft.IconButton(
    icon=ft.Icons.MENU,
    tooltip="메뉴",
    on_click=menu_clicked,
            ),
                ],
            )

    # ==============================
    # 오른쪽 메뉴판
    # ==============================

    async def show_drawer_dialog(title, message):
        await page.close_end_drawer()

        dialog = ft.AlertDialog(
            title=ft.Text(
                title,
                weight=ft.FontWeight.BOLD,
            ),
            content=ft.Text(
                message,
                size=15,
            ),
            actions=[
                ft.TextButton(
                    "확인",
                    on_click=lambda e: page.pop_dialog(),
                ),
            ],
        )

        page.show_dialog(dialog)

    async def schedule_clicked(e):
        await show_drawer_dialog(
            "행사 일정",
            "AGF 2026\n\n"
            "2026년 12월 4일(금)\n"
            "2026년 12월 5일(토)\n"
            "2026년 12월 6일(일)",
        )

    async def venue_clicked(e):
        await show_drawer_dialog(
            "행사장 안내",
            "행사장 정보는 공식 자료가 공개되면 "
            "업데이트할 예정입니다.",
        )

    async def event_info_clicked(e):
        await show_drawer_dialog(
            "행사 정보",
            "AGF 2026\n\n"
            "Anime × Game Festival",
        )

    async def official_homepage_clicked(e):
        await page.close_end_drawer()

    async def official_x_clicked(e):
        await page.close_end_drawer()

    async def official_instagram_clicked(e):
        await page.close_end_drawer()

    async def app_settings_clicked(e):
        await page.close_end_drawer()
        navigation.selected_index = 4
        change_page(index=4)

    # 오른쪽 Drawer
    drawer = ft.NavigationDrawer(
        width=320,
        controls=[
            # 헤더
            ft.Container(
                padding=ft.Padding(
                    left=24,
                    right=20,
                    top=24,
                    bottom=20,
                ),
                content=ft.Column(
                    spacing=4,
                    controls=[
                        ft.Text(
                            "AGF 2026",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            "Anime × Game Festival",
                            size=13,
                            color="#666666",
                        ),
                    ],
                ),
            ),

            ft.Divider(),

            # 행사 안내
            ft.Container(
                padding=ft.Padding(
                    left=24,
                    top=8,
                    right=20,
                    bottom=4,
                ),
                content=ft.Text(
                    "행사 안내",
                    size=13,
                    color="#777777",
                    weight=ft.FontWeight.BOLD,
                ),
            ),

            ft.ListTile(
                leading=ft.Icon(
                    ft.Icons.CALENDAR_MONTH_OUTLINED,
                ),
                title=ft.Text("행사 일정"),
                trailing=ft.Icon(
                    ft.Icons.CHEVRON_RIGHT,
                ),
                on_click=schedule_clicked,
            ),

            ft.ListTile(
                leading=ft.Icon(
                    ft.Icons.LOCATION_ON_OUTLINED,
                ),
                title=ft.Text("행사장 안내"),
                trailing=ft.Icon(
                    ft.Icons.CHEVRON_RIGHT,
                ),
                on_click=venue_clicked,
            ),

            ft.ListTile(
                leading=ft.Icon(
                    ft.Icons.INFO_OUTLINED,
                ),
                title=ft.Text("행사 정보"),
                trailing=ft.Icon(
                    ft.Icons.CHEVRON_RIGHT,
                ),
                on_click=event_info_clicked,
            ),

            ft.Divider(),

            # 공식 채널
            ft.Container(
                padding=ft.Padding(
                    left=24,
                    top=8,
                    right=20,
                    bottom=4,
                ),
                content=ft.Text(
                    "공식 채널",
                    size=13,
                    color="#777777",
                    weight=ft.FontWeight.BOLD,
                ),
            ),

            ft.ListTile(
                leading=ft.Icon(
                    ft.Icons.LANGUAGE,
                ),
                title=ft.Text("공식 홈페이지"),
                url="https://www.agfkorea.com/",
trailing=ft.Icon(
                    ft.Icons.OPEN_IN_NEW,
                ),
                on_click=official_homepage_clicked,
            ),

            ft.ListTile(
                leading=ft.Icon(
                    ft.Icons.ALTERNATE_EMAIL,
                ),
                title=ft.Text("공식 X"),
                url="https://x.com/AGF_Korea",
trailing=ft.Icon(
                    ft.Icons.OPEN_IN_NEW,
                ),
                on_click=official_x_clicked,
            ),

            ft.ListTile(
                leading=ft.Icon(
                    ft.Icons.PHOTO_CAMERA_OUTLINED,
                ),
                title=ft.Text("공식 Instagram"),
                url="https://www.instagram.com/agf_korea/",
trailing=ft.Icon(
                    ft.Icons.OPEN_IN_NEW,
                ),
                on_click=official_instagram_clicked,
            ),

            ft.ListTile(
                leading=ft.Icon(
                    ft.Icons.SETTINGS_OUTLINED,
                ),
                title=ft.Text("앱 설정"),
                trailing=ft.Icon(
                    ft.Icons.CHEVRON_RIGHT,
                ),
                on_click=app_settings_clicked,
            ),
        ],
    )

    # 오른쪽 Drawer 연결
    page.end_drawer = drawer

    # 시작 화면은 홈 AppBar
    set_appbar(0)

   
    # ==============================
    # 앱 설정
    # ==============================
    def more_view():

        def notification_changed(e):
            nonlocal notifications_enabled

            notifications_enabled = e.control.value
            save_settings()

            print(
                "새소식 자동 확인:",
                "ON" if notifications_enabled else "OFF",
            )

        return ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=0,
            controls=[

                # 제목
                ft.Container(
                    padding=ft.Padding(
                        left=20,
                        right=20,
                        top=20,
                        bottom=16,
                    ),
                    content=ft.Text(
                        "앱 설정",
                        size=26,
                        weight=ft.FontWeight.BOLD,
                    ),
                ),

                # 알림
                ft.Container(
                    padding=ft.Padding(
                        left=20,
                        right=20,
                        top=8,
                        bottom=8,
                    ),
                    content=ft.Text(
                        "알림",
                        size=13,
                        color="#777777",
                        weight=ft.FontWeight.BOLD,
                    ),
                ),

                ft.Container(
                    margin=ft.Margin(
                        left=12,
                        right=12,
                        bottom=12,
                    ),
                    border_radius=14,
                    bgcolor="#F5F5F5",
                    content=ft.ListTile(
                        leading=ft.Icon(
                            ft.Icons.NOTIFICATIONS_OUTLINED,
                        ),
                        title=ft.Text(
                            "새소식 자동 확인",
                            size=16,
                        ),
                        subtitle=ft.Text(
                            "AGF 2026의 새로운 소식을 자동으로 확인합니다.",
                            size=13,
                        ),
                        trailing=ft.Switch(
                            value=notifications_enabled,
                            on_change=notification_changed,
                        ),
                    ),
                ),

                # 일반
                ft.Container(
                    padding=ft.Padding(
                        left=20,
                        right=20,
                        top=8,
                        bottom=8,
                    ),
                    content=ft.Text(
                        "일반",
                        size=13,
                        color="#777777",
                        weight=ft.FontWeight.BOLD,
                    ),
                ),

                ft.Container(
                    margin=ft.Margin(
                        left=12,
                        right=12,
                        bottom=12,
                    ),
                    border_radius=14,
                    bgcolor="#F5F5F5",
                    content=ft.Column(
                        spacing=0,
                        controls=[

                            ft.ListTile(
                                leading=ft.Icon(
                                    ft.Icons.SAVE_OUTLINED,
                                ),
                                title=ft.Text(
                                    "설정 저장",
                                    size=16,
                                ),
                                subtitle=ft.Text(
                                    "알림 설정이 자동으로 저장됩니다.",
                                    size=13,
                                ),
                            ),

                            ft.Divider(
                                height=1,
                            ),

                            ft.ListTile(
                                leading=ft.Icon(
                                    ft.Icons.INFO_OUTLINED,
                                ),
                                title=ft.Text(
                                    "행사 정보",
                                    size=16,
                                ),
                                subtitle=ft.Text(
                                    "행사 일정 및 행사 안내는 메뉴에서 확인할 수 있습니다.",
                                    size=13,
                                ),
                                trailing=ft.Icon(
                                    ft.Icons.CHEVRON_RIGHT,
                                ),
                                on_click=event_info_clicked,
                            ),
                        ],
                    ),
                ),

                # 앱 정보
                ft.Container(
                    padding=ft.Padding(
                        left=20,
                        right=20,
                        top=8,
                        bottom=8,
                    ),
                    content=ft.Text(
                        "앱 정보",
                        size=13,
                        color="#777777",
                        weight=ft.FontWeight.BOLD,
                    ),
                ),

                ft.Container(
                    margin=ft.Margin(
                        left=12,
                        right=12,
                        bottom=20,
                    ),
                    border_radius=14,
                    bgcolor="#F5F5F5",
                    content=ft.Column(
                        spacing=0,
                        controls=[

                            ft.ListTile(
                                leading=ft.Icon(
                                    ft.Icons.EVENT_OUTLINED,
                                ),
                                title=ft.Text(
                                    "AGF 2026",
                                    size=16,
                                ),
                                subtitle=ft.Text(
                                    "Anime × Game Festival",
                                    size=13,
                                ),
                            ),

                            ft.Divider(
                                height=1,
                            ),

                            ft.ListTile(
                                leading=ft.Icon(
                                    ft.Icons.INFO_OUTLINED,
                                ),
                                title=ft.Text(
                                    "버전",
                                    size=16,
                                ),
                                trailing=ft.Text(
                                    "1.0.0",
                                    size=14,
                                    color="#777777",
                                ),
                            ),
                        ],
                    ),
                ),
            ],
        )

    # 뉴스 카드
    def build_news_card(item):
        return ft.Container(
            padding=20,
            border_radius=15,
            bgcolor="#F5F5F5",
            content=ft.Column(
                controls=[
                    ft.Text(
                        item["title"],
                        size=18,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Button(
                         "공지 원문 열기",
                         icon=ft.Icons.OPEN_IN_NEW,
                         action=ft.OpenUrl(
                             urljoin(
                                 "https://www.agfkorea.com",
                                 item["url"],
                             ),
                             target=ft.UrlTarget.BLANK,
                         ),
                    ),
                ],
            ),
        )
    def get_filtered_news():
        if news_category == "전체":
            return all_news_items

        if news_category == "공지":
            return [
                item for item in all_news_items
                if item.get("category") == "공지"
            ]

        if news_category == "행사소식":
            return [
                item for item in all_news_items
                if item.get("category") == "행사소식"
            ]

        if news_category == "SNS":
            return [
                item for item in all_news_items
                if item.get("category") == "SNS"
                and item.get("sub_category") == news_sub_category
            ]

        return []

    # 뉴스 새로고침
    # 뉴스 새로고침
    def refresh_news(e=None):
        nonlocal all_news_items

        if news_content is None:
            return

        all_news_items = fetch_all_news() or []

        news_content.controls.clear()

        filtered_items = get_filtered_news()

        if not filtered_items:
            news_content.controls.append(
                ft.Container(
                    padding=20,
                    border_radius=15,
                    bgcolor="#F5F5F5",
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "새로운 소식이 없습니다.",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                "현재 선택한 카테고리에 등록된 소식이 없습니다.",
                                size=14,
                            ),
                        ],
                    ),
                )
            )
        else:
            for item in filtered_items:
                news_content.controls.append(
                    build_news_card(item)
                )

        page.update()

    # 하단 메뉴
    navigation = ft.NavigationBar(
    destinations=[
        ft.NavigationBarDestination(
            icon=ft.Icons.HOME_OUTLINED,
            selected_icon=ft.Icons.HOME,
            label="홈",
        ),
        ft.NavigationBarDestination(
            icon=ft.Icons.NEWSPAPER_OUTLINED,
            selected_icon=ft.Icons.NEWSPAPER,
            label="뉴스",
        ),
        ft.NavigationBarDestination(
            icon=ft.Icons.MIC_OUTLINED,
            selected_icon=ft.Icons.MIC,
            label="스테이지",
        ),
        ft.NavigationBarDestination(
            icon=ft.Icons.STORE_OUTLINED,
            selected_icon=ft.Icons.STORE,
            label="부스",
        ),
        ft.NavigationBarDestination(
            icon=ft.Icons.SETTINGS_OUTLINED,
            selected_icon=ft.Icons.SETTINGS,
            label="설정",
        ),
    ],
)
 
   # ==============================
    # 홈 화면 임시 UI
    # ==============================

    # 최신 소식
    home_news = ft.Container(
        margin=ft.Margin(
            left=20,
            right=20,
            top=12,
            bottom=8,
        ),
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(
                            "📰 최신 소식",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.TextButton(
                            "전체보기 ›",
                            on_click=lambda e: change_page(index=1),
                        ),
                    ],
                ),

                ft.Container(
                    padding=12,
                    border_radius=10,
                    bgcolor="#F5F5F5",
                    on_click=lambda e: change_page(index=1),
                    content=ft.Row(
                        controls=[
                            ft.Text(
                                "AGF 2026 새로운 소식입니다.",
                                size=14,
                                expand=True,
                            ),
                            ft.Icon(
                                ft.Icons.CHEVRON_RIGHT,
                                size=20,
                            ),
                        ],
                    ),
                ),

                ft.Container(
                    padding=12,
                    border_radius=10,
                    bgcolor="#F5F5F5",
                    on_click=lambda e: change_page(index=1),
                    content=ft.Row(
                        controls=[
                            ft.Text(
                                "새로운 게스트 소식을 확인해보세요.",
                                size=14,
                                expand=True,
                            ),
                            ft.Icon(
                                ft.Icons.CHEVRON_RIGHT,
                                size=20,
                            ),
                        ],
                    ),
                ),

                ft.Container(
                    padding=12,
                    border_radius=10,
                    bgcolor="#F5F5F5",
                    on_click=lambda e: change_page(index=1),
                    content=ft.Row(
                        controls=[
                            ft.Text(
                                "행사 관련 최신 안내가 업데이트됩니다.",
                                size=14,
                                expand=True,
                            ),
                            ft.Icon(
                                ft.Icons.CHEVRON_RIGHT,
                                size=20,
                            ),
                        ],
                    ),
                ),
            ],
        ),
    )
    
    # 티켓 카드
    ticket_card = ft.Container(
        margin=ft.Margin(
            left=20,
            right=20,
            top=8,
            bottom=8,
        ),
        padding=20,
        border_radius=16,
        bgcolor="#F5F5F5",
        url="https://www.agfkorea.com/ticket",
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Row(
                    spacing=12,
                    controls=[
                        ft.Text(
                            "🎟️",
                            size=28,
                        ),
                        ft.Column(
                            spacing=3,
                            controls=[
                                ft.Text(
                                    "티켓 예매",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    f"{AGF_TITLE} 티켓을 예매하세요.",
                                    size=13,
                                    color="#666666",
                                ),
                            ],
                        ),
                    ],
                ),
                ft.Icon(
                    ft.Icons.OPEN_IN_NEW,
                    size=22,
                ),
            ],
        ),
    )

    # 스폰서 카드
    sponsor_card = ft.Container(
        padding=24,
        border_radius=18,
        bgcolor="#F5F5F5",
        content=ft.Column(
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Text(
                    "⭐ 메인 스폰서 & 스폰서",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    f"{AGF_TITLE}의 메인 스폰서와 참가 스폰서를 확인하세요.",
                    size=15,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "스폰서 정보 공개 후 업데이트 예정",
                    size=13,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
        ),
    )
    # 게스트 카드
    guest_card = ft.Container(
        padding=24,
        border_radius=18,
        bgcolor="#F5F5F5",
        on_click=lambda e: change_page(index=2),
        content=ft.Column(
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Text(
                    "🎤 게스트",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    f"{AGF_TITLE} 공식 게스트 정보를 확인하세요.",
                    size=15,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "게스트 정보 공개 후 업데이트 예정",
                    size=13,
                    color="#666666",
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
        ),
    )

    # 스테이지 카드
    stage_card = ft.Container(
        padding=24,
        border_radius=18,
        bgcolor="#F5F5F5",
        on_click=lambda e: change_page(index=2),
        content=ft.Column(
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Text(
                    "🎤 스테이지",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    f"{AGF_TITLE} 스테이지 일정을 확인하세요.",
                    size=15,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "스테이지 정보 공개 후 업데이트 예정",
                    size=13,
                    color="#666666",
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
        ),
    )

    # ==============================
    # 홈 스와이프 영역
    # ==============================

    home_page_view = ft.PageView(
        height=190,
        viewport_fraction=0.90,
        horizontal=True,
        snap=True,
        controls=[
            sponsor_card,
            guest_card,
            stage_card,
        ],
    )

    # 스와이프 인디케이터
    home_page_indicator = ft.Text(
        "● ○ ○",
        size=12,
        text_align=ft.TextAlign.CENTER,
    )

    def home_page_changed(e):
        index = e.control.selected_index

        indicators = [
            "● ○ ○",
            "○ ● ○",
            "○ ○ ●",
        ]

        home_page_indicator.value = indicators[index]
        home_page_indicator.update()

    home_page_view.on_change = home_page_changed

    # 이전 카드
    async def previous_home_card(e):
        current_index = home_page_view.selected_index

        if current_index > 0:
            await home_page_view.previous_page()

    # 다음 카드
    async def next_home_card(e):
        current_index = home_page_view.selected_index

        if current_index < len(home_page_view.controls) - 1:
            await home_page_view.next_page()

    # 마우스 드래그
    async def home_drag_end(e):
        velocity = e.primary_velocity

        if velocity is None:
            return

        if velocity < -100:
            await next_home_card(e)

        elif velocity > 100:
            await previous_home_card(e)

    home_page_gesture = ft.GestureDetector(
        on_horizontal_drag_end=home_drag_end,
        content=home_page_view,
    )

    # 좌우 화살표
    home_swipe_area = ft.Stack(
        height=190,
        controls=[
            home_page_gesture,

            ft.Container(
                left=4,
                top=70,
                content=ft.IconButton(
                    icon=ft.Icons.CHEVRON_LEFT,
                    icon_size=30,
                    tooltip="이전",
                    on_click=previous_home_card,
                ),
            ),

            ft.Container(
                right=4,
                top=70,
                content=ft.IconButton(
                    icon=ft.Icons.CHEVRON_RIGHT,
                    icon_size=30,
                    tooltip="다음",
                    on_click=next_home_card,
                ),
            ),
        ],
    )

    beta_banner = ft.Container(height=0)
    if is_web:
        beta_banner = ft.Container(
            margin=ft.Margin(left=20, right=20, top=10, bottom=8),
            padding=ft.Padding(left=14, right=14, top=10, bottom=10),
            border_radius=12,
            bgcolor="#FFF4E5",
            content=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.FLARE_OUTLINED, size=18),
                    ft.Column(
                        spacing=2,
                        expand=True,
                        controls=[
                            ft.Text(
                                "BETA · 비공식 테스트 버전",
                                size=13,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                "현재 개발 중인 테스트 사이트입니다.",
                                size=12,
                                color="#666666",
                            ),
                        ],
                    ),
                ],
            ),
        )

    def build_home_view():
        return ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=0,
            controls=[

                beta_banner,

                # 최신 뉴스
                home_news,
                
                # 티켓
                ticket_card,

                # 스와이프 카드
                ft.Container(
                    margin=ft.Margin(
                        left=0,
                        right=0,
                        top=8,
                        bottom=4,
                    ),
                    content=home_swipe_area,
                ),

                ft.Container(
                    alignment=ft.Alignment.CENTER,
                    padding=6,
                    content=home_page_indicator,
                ),

            ],
        )
    def news_tab_changed(e):
        nonlocal news_category

        categories = [
            "전체",
            "공지",
            "행사소식",
            "SNS",
            "공개",
        ]

        news_category = categories[e.control.selected_index]

        if news_content is not None:
            news_content.controls.clear()

            filtered_items = get_filtered_news()

            if not filtered_items:
                news_content.controls.append(
                    ft.Container(
                        padding=20,
                        border_radius=15,
                        bgcolor="#F5F5F5",
                        content=ft.Column(
                            controls=[
                                ft.Text(
                                    "새로운 소식이 없습니다.",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    "현재 선택한 카테고리에 등록된 소식이 없습니다.",
                                    size=14,
                                ),
                            ],
                        ),
                    )
                )
            else:
                for item in filtered_items:
                    news_content.controls.append(
                        build_news_card(item)
                    )

        page.update()
        
    # 화면 전환
    def change_page(e=None, index=None):
        nonlocal news_content

        if index is None:
            index = e.control.selected_index

        navigation.selected_index = index
        set_appbar(index)

        if index == 0:
            content_area.content = build_home_view()

        elif index == 1:
            # ==============================
            # AGF 뉴스
            # ==============================

            news_content = ft.Column(
                spacing=10,
                controls=[
                    ft.Text(
                        "공식 공지를 확인하는 중...",
                        size=14,
                    )
                ],
            )

            news_tabs = ft.TabBar(
                scrollable=True,
                tab_alignment=ft.TabAlignment.START,
                indicator_thickness=3,
                tabs=[
                    ft.Tab(label="전체"),
                    ft.Tab(label="공지"),
                    ft.Tab(label="행사소식"),
                    ft.Tab(label="SNS"),
                    ft.Tab(label="공개"),
                ],
            )

            news_tabs_container = ft.Tabs(
                length=5,
                selected_index=0,
                on_change=news_tab_changed,
                content=news_tabs,
            )

            content_area.content = ft.Column(
                expand=True,    
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.Container(
                        padding=ft.Padding(
                            left=20,
                            right=20,
                            top=20,
                            bottom=10,
                        ),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(
                                    "AGF 뉴스",
                                    size=26,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Button(
                                    "새로고침",
                                    icon=ft.Icons.REFRESH,
                                    on_click=refresh_news,
                                ),
                            ],
                        ),
                    ),

                    # 상단 카테고리
                    news_tabs_container,

                    # 뉴스 내용
                    ft.Container(
                        padding=ft.Padding(
                            left=20,
                            right=20,
                            top=10,
                            bottom=20,
                        ),
                        content=news_content,
                    ),
                ],
            )

            refresh_news()

        elif index == 2:
            # ==============================
            # 스테이지 임시 데이터
            # ==============================

            stage_data = {
                "12월 4일(금)": {
                    "Red": [
                        {
                            "time": "10:30",
                            "title": "오프닝 스테이지",
                            "guest": "게스트 A",
                        },
                        {
                            "time": "13:00",
                            "title": "스페셜 토크",
                            "guest": "게스트 B",
                        },
                        {
                            "time": "15:30",
                            "title": "메인 스테이지",
                            "guest": "게스트 C",
                        },
                    ],
                    "Blue": [
                        {
                            "time": "11:00",
                            "title": "블루 스테이지 오프닝",
                            "guest": "게스트 D",
                        },
                        {
                            "time": "14:00",
                            "title": "게스트 토크",
                            "guest": "게스트 E",
                        },
                        {
                            "time": "16:00",
                            "title": "블루 스테이지 피날레",
                            "guest": "게스트 F",
                        },
                    ],
                },

                "12월 5일(토)": {
                    "Red": [
                        {
                            "time": "11:00",
                            "title": "스페셜 스테이지",
                            "guest": "게스트 G",
                        },
                        {
                            "time": "14:00",
                            "title": "게스트 토크",
                            "guest": "게스트 H",
                        },
                        {
                            "time": "16:00",
                            "title": "메인 스테이지",
                            "guest": "게스트 I",
                        },
                    ],
                    "Blue": [
                        {
                            "time": "10:30",
                            "title": "블루 스페셜",
                            "guest": "게스트 J",
                        },
                        {
                            "time": "13:30",
                            "title": "토크 스테이지",
                            "guest": "게스트 K",
                        },
                        {
                            "time": "15:30",
                            "title": "블루 피날레",
                            "guest": "게스트 L",
                        },
                    ],
                },

                "12월 6일(일)": {
                    "Red": [
                        {
                            "time": "11:00",
                            "title": "파이널 스테이지",
                            "guest": "게스트 M",
                        },
                        {
                            "time": "13:30",
                            "title": "스페셜 토크",
                            "guest": "게스트 N",
                        },
                        {
                            "time": "16:00",
                            "title": "클로징 스테이지",
                            "guest": "게스트 O",
                        },
                    ],
                    "Blue": [
                        {
                            "time": "10:30",
                            "title": "블루 파이널",
                            "guest": "게스트 P",
                        },
                        {
                            "time": "13:00",
                            "title": "블루 스페셜 토크",
                            "guest": "게스트 Q",
                        },
                        {
                            "time": "15:30",
                            "title": "블루 클로징",
                            "guest": "게스트 R",
                        },
                    ],
                },
            }
            # ==============================
            # 게스트 정보
            # 실제 게스트 공개 후 이 부분만 수정
            # ==============================

            guest_data = {
                "게스트 A": {
                    "name": "게스트 A",
                    "role": "성우 / 게스트",
                    "description": "게스트 A의 소개 정보입니다.",
                    "image": None,
                },
                "게스트 B": {
                    "name": "게스트 B",
                    "role": "성우 / 게스트",
                    "description": "게스트 B의 소개 정보입니다.",
                    "image": None,
                },
                "게스트 C": {
                    "name": "게스트 C",
                    "role": "성우 / 게스트",
                    "description": "게스트 C의 소개 정보입니다.",
                    "image": None,
                },
            }

            def show_guest_detail(guest_name):
                guest = guest_data.get(
                    guest_name,
                    {
                        "name": guest_name,
                        "role": "AGF 2026 공식 게스트",
                        "description": "공식 발표 후 업데이트할 예정입니다.",
                        "image": None,
                    },
                )

                # 게스트 출연 일정 찾기
                guest_schedule = []

                for date_name, stages in stage_data.items():
                    for stage_name, items in stages.items():
                        for item in items:
                            if item["guest"] == guest_name:
                                guest_schedule.append(
                                    {
                                        "date": date_name,
                                        "stage": stage_name,
                                        "time": item["time"],
                                        "title": item["title"],
                                    }
                                )

                # 게스트 상세 화면 AppBar
                page.appbar = ft.AppBar(
                    leading=ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        tooltip="스테이지로",
                        on_click=lambda e: change_page(index=2),
                    ),
                    title=ft.Text(
                        "게스트 정보",
                        size=21,
                        weight=ft.FontWeight.BOLD,
                    ),
                    center_title=False,
                    bgcolor="#FFFFFF",
                    elevation=2,
                    toolbar_height=68,
                    actions=[
                        ft.IconButton(
                            icon=ft.Icons.NOTIFICATIONS_OUTLINED,
                            tooltip="알림",
                            on_click=notification_clicked,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.MENU,
                            tooltip="메뉴",
                            on_click=menu_clicked,
                        ),
                    ],
                )

                # 출연 일정
                schedule_controls = []

                if guest_schedule:
                    for schedule in guest_schedule:
                        schedule_controls.append(
                            ft.Container(
                                padding=15,
                                border_radius=12,
                                bgcolor="#F5F5F5",
                                content=ft.Row(
                                    spacing=12,
                                    controls=[
                                        ft.Column(
                                            spacing=3,
                                            controls=[
                                                ft.Text(
                                                    schedule["date"],
                                                    size=13,
                                                    color="#666666",
                                                ),
                                                ft.Text(
                                                    schedule["stage"],
                                                    size=15,
                                                    weight=ft.FontWeight.BOLD,
                                                ),
                                            ],
                                        ),
                                        ft.Container(
                                            expand=True,
                                            content=ft.Column(
                                                spacing=3,
                                                controls=[
                                                    ft.Text(
                                                        schedule["time"],
                                                        size=14,
                                                        weight=ft.FontWeight.BOLD,
                                                    ),
                                                    ft.Text(
                                                        schedule["title"],
                                                        size=14,
                                                    ),
                                                ],
                                            ),
                                        ),
                                    ],
                                ),
                            )
                        )
                else:
                    schedule_controls.append(
                        ft.Text(
                            "출연 일정 정보가 없습니다.",
                            size=14,
                            color="#666666",
                        )
                    )

                # 게스트 상세 화면
                content_area.content = ft.Column(
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        # 프로필 영역
                        ft.Container(
                            padding=20,
                            content=ft.Column(
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=12,
                                controls=[
                                    ft.Container(
                                        width=140,
                                        height=140,
                                        border_radius=70,
                                        bgcolor="#F0F0F0",
                                        alignment=ft.Alignment.CENTER,
                                        content=ft.Icon(
                                            ft.Icons.PERSON_OUTLINE,
                                            size=70,
                                        ),
                                    ),

                                    ft.Text(
                                        guest["name"],
                                        size=24,
                                        weight=ft.FontWeight.BOLD,
                                        text_align=ft.TextAlign.CENTER,
                                    ),

                                    ft.Text(
                                       guest["role"],
                                       size=14,
                                       color="#666666",
                                       text_align=ft.TextAlign.CENTER,
                                     ),                                
                                 ],
                            ),
                        ),

                        # 게스트 소개
                        ft.Container(
                            margin=ft.Margin(
                                left=20,
                                right=20,
                                bottom=15,
                            ),
                            padding=20,
                            border_radius=15,
                            bgcolor="#F5F5F5",
                            content=ft.Column(
                                spacing=8,
                                controls=[
                                    ft.Text(
                                        "게스트 소개",
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        guest["description"],
                                        size=14,
                                    ),
                                ],
                            ),
                        ),

                        # 출연 일정
                        ft.Container(
                            margin=ft.Margin(
                                left=20,
                                right=20,
                                bottom=20,
                            ),
                            padding=20,
                            border_radius=15,
                            bgcolor="#FFFFFF",
                            content=ft.Column(
                                spacing=10,
                                controls=[
                                    ft.Text(
                                        "출연 스테이지",
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    *schedule_controls,
                                ],
                            ),
                        ),

                        ft.Container(
                            margin=ft.Margin(
                                left=20,
                                right=20,
                                bottom=20,
                            ),
                            alignment=ft.Alignment.CENTER,
                            content=ft.Text(
                                "※ 실제 게스트 정보 공개 후 "
                                "프로필과 출연 정보를 업데이트합니다.",
                                size=12,
                                color="#777777",
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ),
                    ],
                )

                page.update()

            def build_stage_schedule(date_name, stage_name):
                schedule_controls = [
                    ft.Text(
                        f"{stage_name} 스테이지",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                    ),
                ]

                items = stage_data[date_name][stage_name]

                for item in items:
                    schedule_controls.append(
                        ft.Container(
                            padding=15,
                            border_radius=14,
                            bgcolor="#FFFFFF",
                            content=ft.Row(
                                spacing=14,
                                controls=[
                                    ft.Container(
                                        width=55,
                                        alignment=ft.Alignment.CENTER,
                                        content=ft.Text(
                                            item["time"],
                                            size=14,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                    ),
                                    ft.Column(
                                        expand=True,
                                        spacing=4,
                                        controls=[
                                            ft.Text(
                                                item["title"],
                                                size=16,
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                            ft.TextButton(
                                                item["guest"],
                                                icon=ft.Icons.PEOPLE_OUTLINED,
                                                on_click=lambda e,
                                                guest=item["guest"]:
                                                    show_guest_detail(guest),
                                            ),
                                        ],
                                    ),
                                    ft.Icon(
                                        ft.Icons.CHEVRON_RIGHT,
                                        size=22,
                                    ),
                                ],
                            ),
                        )
                    )

                schedule_controls.append(
                    ft.Text(
                        "※ 실제 스테이지 및 게스트 정보 공개 후 "
                        "업데이트됩니다.",
                        size=12,
                        color="#777777",
                    )
                )

                return ft.Column(
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                    controls=schedule_controls,
                )

            # ==============================
            # 스테이지 → 날짜 순서
            # ==============================

            stage_tabs = []

            for stage_name in ["Red", "Blue"]:

                date_tabs = []

                for date_name in stage_data.keys():
                    date_tabs.append(
                        ft.Container(
                            padding=10,
                            content=build_stage_schedule(
                                date_name,
                                stage_name,
                            ),
                        )
                    )

                stage_tabs.append(
                    ft.Container(
                        padding=10,
                        content=ft.Tabs(
                            length=3,
                            selected_index=0,
                            content=ft.Column(
                                expand=True,
                                controls=[
                                    # 날짜 선택
                                    ft.TabBar(
                                        scrollable=False,
                                        tab_alignment=ft.TabAlignment.FILL,
                                        indicator_thickness=3,
                                        tabs=[
                                            ft.Tab(
                                                label="12/4",
                                            ),
                                            ft.Tab(
                                                label="12/5",
                                            ),
                                            ft.Tab(
                                                label="12/6",
                                            ),
                                        ],
                                    ),

                                    ft.Container(
                                        height=500,
                                        content=ft.TabBarView(
                                            controls=date_tabs,
                                        ),
                                    ),
                                ],
                            ),
                        ),
                    )
                )

            content_area.content = ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.Container(
                        padding=20,
                        content=ft.Column(
                            spacing=5,
                            controls=[
                                ft.Text(
                                    "AGF 스테이지",
                                    size=26,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    "스테이지와 날짜를 선택해 "
                                    "일정을 확인하세요.",
                                    size=14,
                                    color="#666666",
                                ),
                            ],
                        ),
                    ),

                    # 스테이지 선택이 먼저
                    ft.Container(
                        margin=ft.Margin(
                            left=20,
                            right=20,
                            bottom=20,
                        ),
                        padding=10,
                        border_radius=15,
                        bgcolor="#F5F5F5",
                        content=ft.Tabs(
                            length=2,
                            selected_index=0,
                            content=ft.Column(
                                expand=True,
                                controls=[
                                    # Red / Blue
                                    ft.TabBar(
                                        scrollable=False,
                                        tab_alignment=ft.TabAlignment.FILL,
                                        indicator_thickness=3,
                                        tabs=[
                                            ft.Tab(
                                                label="Red",
                                            ),
                                            ft.Tab(
                                                label="Blue",
                                            ),
                                        ],
                                    ),

                                    # 날짜 선택
                                    ft.Container(
                                        height=560,
                                        content=ft.TabBarView(
                                            controls=stage_tabs,
                                        ),
                                    ),
                                ],
                            ),
                        ),
                    ),
                ],
            )

        elif index == 3:
            # ==============================
            # AGF 부스 - 임시 UI
            # ==============================

            def show_participant_detail(item):
                dialog = ft.AlertDialog(
                    title=ft.Text(
                        item["name"],
                        weight=ft.FontWeight.BOLD,
                    ),
                    content=ft.Text(
                        f"부스 번호: {item['booth']}\n\n"
                        "참가사 상세 정보는 공식 자료 공개 후 "
                        "업데이트할 예정입니다."
                    ),
                    actions=[
                        ft.TextButton(
                            "확인",
                            on_click=lambda e: page.pop_dialog(),
                        ),
                    ],
                )
                page.show_dialog(dialog)

            search_field = ft.TextField(
                hint_text="참가사 검색",
                prefix_icon=ft.Icons.SEARCH,
                border_radius=10,
            )

            participant_list = ft.Column(
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            )

            def update_participants(e=None):
                keyword = (search_field.value or "").strip().lower()

                participant_list.controls.clear()

                for item in participants:
                    if keyword and keyword not in item["name"].lower():
                        continue

                    participant_list.controls.append(
                        ft.Container(
                            padding=15,
                            border_radius=10,
                            bgcolor="#FFFFFF",
                            on_click=lambda e, item=item:
                                show_participant_detail(item),
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Column(
                                        spacing=3,
                                        controls=[
                                            ft.Text(
                                                item["name"],
                                                size=16,
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                            ft.Text(
                                                f"부스 {item['booth']}",
                                                size=13,
                                                color="#666666",
                                            ),
                                        ],
                                    ),
                                    ft.Icon(
                                        ft.Icons.CHEVRON_RIGHT,
                                        size=22,
                                    ),
                                ],
                            ),
                        )
                    )

                if not participant_list.controls:
                    participant_list.controls.append(
                        ft.Text(
                            "검색 결과가 없습니다.",
                            size=14,
                        )
                    )

                page.update()

            search_field.on_change = update_participants

            update_participants()

            # ==============================
            # 부스 & 배치도
            # ==============================

            booth_list = ft.Column(
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            )

            def show_booth_detail(item):
                dialog = ft.AlertDialog(
                    title=ft.Text(
                        f"부스 {item['booth']}",
                        weight=ft.FontWeight.BOLD,
                    ),
                    content=ft.Column(
                        spacing=8,
                        controls=[
                            ft.Text(
                                item["name"],
                                size=18,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                f"부스 번호: {item['booth']}",
                                size=14,
                            ),
                            ft.Divider(),
                            ft.Text(
                                "참가사 상세 정보는 공식 자료 공개 후 "
                                "업데이트할 예정입니다.",
                                size=13,
                            ),
                        ],
                    ),
                    actions=[
                        ft.TextButton(
                            "확인",
                            on_click=lambda e: page.pop_dialog(),
                        ),
                    ],
                )

                page.show_dialog(dialog)

            for item in participants:
                booth_list.controls.append(
                    ft.Container(
                        padding=15,
                        border_radius=12,
                        bgcolor="#FFFFFF",
                        on_click=lambda e, item=item:
                            show_booth_detail(item),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Column(
                                    spacing=3,
                                    controls=[
                                        ft.Text(
                                            item["booth"],
                                            size=16,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Text(
                                            item["name"],
                                            size=14,
                                        ),
                                    ],
                                ),
                                ft.Icon(
                                    ft.Icons.CHEVRON_RIGHT,
                                    size=22,
                                ),
                            ],
                        ),
                    )
                )

            # 배치도
            if map_file.exists():
                map_view = ft.Container(
                    height=350,
                    alignment=ft.Alignment.CENTER,
                    border_radius=12,
                    bgcolor="#FFFFFF",
                    content=ft.Image(
                        src=map_file.read_bytes(),
                        width=float("inf"),
                        height=330,
                        fit=ft.BoxFit.CONTAIN,
                        error_content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            alignment=ft.MainAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(
                                    ft.Icons.MAP_OUTLINED,
                                    size=50,
                                ),
                                ft.Text(
                                    "배치도 이미지를 불러오지 못했습니다.",
                                    size=15,
                                ),
                            ],
                        ),
                    ),
                )
            else:
                map_view = ft.Container(
                    height=350,
                    alignment=ft.Alignment.CENTER,
                    border_radius=12,
                    bgcolor="#FFFFFF",
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=8,
                        controls=[
                            ft.Icon(
                                ft.Icons.MAP_OUTLINED,
                                size=55,
                            ),
                            ft.Text(
                                "AGF 2026 부스 배치도",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                "실제 배치도 공개 후 업데이트 예정",
                                size=13,
                                color="#666666",
                            ),
                        ],
                    ),
                )

            content_area.content = ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.Container(
                        padding=20,
                        content=ft.Text(
                            "AGF 부스",
                            size=26,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ),

                    ft.Container(
                        margin=ft.Margin(
                            left=20,
                            right=20,
                            top=0,
                            bottom=10,
                        ),
                        padding=20,
                        border_radius=15,
                        bgcolor="#F5F5F5",
                        content=ft.Column(
                            spacing=8,
                            controls=[
                                ft.Text(
                                    "참가사 · 부스 · 배치도",
                                    size=20,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    "참가사와 부스 위치를 임시로 확인할 수 있습니다.",
                                    size=14,
                                ),
                            ],
                        ),
                    ),

                    ft.Container(
                        margin=ft.Margin(
                            left=20,
                            right=20,
                            bottom=20,
                        ),
                        padding=10,
                        border_radius=15,
                        bgcolor="#F5F5F5",
                        content=ft.Tabs(
                            length=2,
                            selected_index=0,
                            content=ft.Column(
                                expand=True,
                                controls=[
                                    ft.TabBar(
                                        scrollable=False,
                                        tab_alignment=ft.TabAlignment.FILL,
                                        indicator_thickness=3,
                                        tabs=[
                                            ft.Tab(
                                                label="참가사",
                                            ),
                                            ft.Tab(
                                                label="부스 & 배치도",
                                            ),
                                        ],
                                    ),

                                    ft.Container(
                                        height=500,
                                        content=ft.TabBarView(
                                            controls=[
                                                # 참가사
                                                ft.Container(
                                                    padding=10,
                                                    content=ft.Column(
                                                        spacing=10,
                                                        controls=[
                                                            ft.Text(
                                                                "참가사 정보",
                                                                size=20,
                                                                weight=ft.FontWeight.BOLD,
                                                            ),

                                                            search_field,

                                                            participant_list,

                                                            ft.Text(
                                                                "※ 현재는 임시 참가사 정보입니다.",
                                                                size=13,
                                                                color="#666666",
                                                            ),
                                                        ],
                                                    ),
                                                ),

                                                # 부스 & 배치도
                                                ft.Container(
                                                    padding=10,
                                                    content=ft.Column(
                                                        spacing=12,
                                                        scroll=ft.ScrollMode.AUTO,
                                                        controls=[
                                                            ft.Text(
                                                                "부스 & 배치도",
                                                                size=20,
                                                                weight=ft.FontWeight.BOLD,
                                                            ),

                                                            ft.Text(
                                                                "부스 번호와 참가사를 확인할 수 있습니다.",
                                                                size=13,
                                                            ),

                                                            map_view,

                                                            ft.Text(
                                                                "부스 목록",
                                                                size=18,
                                                                weight=ft.FontWeight.BOLD,
                                                            ),

                                                            booth_list,

                                                            ft.Text(
                                                                "※ 실제 배치도와 참가사 정보 공개 후 업데이트됩니다.",
                                                                size=12,
                                                                color="#666666",
                                                           ),
                                                        ],
                                                    ),
                                                ),
                                            ],
                                        ),
                                    ),
                                ],
                            ),
                        ),
                    ),
                ],
            )


        elif index == 4:
            content_area.content = more_view()

        page.update()

    # 하단 메뉴 연결
    navigation.on_change = change_page
    # 콘텐츠 영역
    content_area = ft.Container(
        expand=True,
        content=build_home_view(),
    )

    page.navigation_bar = navigation

     # 55분마다 공식 공지 + X + Instagram 확인
    async def auto_refresh_news():
        nonlocal news_initialized

        while True:
            # 55분 = 3300초
            await asyncio.sleep(3300)

            if not notifications_enabled:
                continue

            news_items = fetch_all_news() or []

            # 첫 확인에서는 현재 올라와 있는 소식을
            # 기존 소식으로 등록하고 알림은 보내지 않음
            if not news_initialized:
                for item in news_items:
                    if item["url"] not in seen_news:
                        seen_news.append(item["url"])

                news_initialized = True
                save_settings()

                print("기존 소식 초기화 완료")
                continue

            # 이미 확인한 소식을 제외하고 새 소식만 찾기
            new_items = []
            batch_urls = set()

            for item in news_items:
                url = item["url"]

                if url in seen_news:
                    continue

                if url in batch_urls:
                    continue

                batch_urls.add(url)
                new_items.append(item)

            if not new_items:
                continue

            # 새 소식 기록
            for item in new_items:
                seen_news.append(item["url"])

            # 뉴스 화면이 열려 있으면 새 소식을 맨 위에 추가
            if news_content is not None:
                for item in reversed(new_items):
                    news_content.controls.insert(
                        0,
                        build_news_card(item),
                    )

            # 새 소식이 있을 때만 Windows 알림
            for item in new_items:
               show_windows_notification(
                    f"{AGF_TITLE} {item['source']} 새소식",
                    item["title"],
                    item["url"],
                )

            save_settings()

            if news_content is not None:
                page.update()

    if not is_web:
        page.run_task(auto_refresh_news)
    page.add(content_area)


if __name__ == "__main__":
    ft.run(main)
