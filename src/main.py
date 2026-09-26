import flet as ft
import json
from pathlib import Path
import urllib.request
from urllib.parse import (
    urljoin,
    quote,
)
from html.parser import HTMLParser
import asyncio
from datetime import date
from email.utils import parsedate_to_datetime
import os
import re
import xml.etree.ElementTree as ET

if os.name == "nt":
    from winotify import Notification
else:
    Notification = None


# ==============================
# AGF 연도 자동화
# ==============================

CURRENT_YEAR = date.today().year
AGF_TITLE = f"AGF {CURRENT_YEAR} 정보"

# 참가사 정보
# 실제 공식 참가사 정보 공개 후 데이터 추가
participants = []

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
                self.news.append(
                    {
                        "title": title,
                        "url": self.current_link,
                    }
                )

            self.current_link = None
            self.current_text = []


def fetch_agf_news():
    url = "https://www.agfkorea.com/customer?idx=1"

    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=10,
        ) as response:
            html = response.read().decode(
                "utf-8",
                errors="ignore",
            )

        parser = NewsParser()
        parser.feed(html)

        news_items = []

        for item in parser.news:
            news_items.append(
                {
                    "title": item["title"],
                    "url": urljoin(
                        "https://www.agfkorea.com",
                        item["url"],
                    ),
                    "category": "공지",
                    "sub_category": "공지",
                    "source": "출처: AGF Korea",
                }
            )

        print(
            f"[공식 뉴스] 가져온 항목 수: "
            f"{len(news_items)}"
        )

        return news_items

    except Exception as e:
        print(
            "AGF 공식 뉴스 불러오기 실패:",
            repr(e),
        )
        return []


def fetch_sns_news():
    news_items = []

    rss_queries = [
        (
            "X",
            "site:x.com/AGF_Korea AGF 2026",
        ),
        (
            "Instagram",
            "site:instagram.com/agf_korea AGF 2026",
        ),
    ]

    for sub_category, query in rss_queries:
        try:
            rss_url = (
                "https://news.google.com/rss/search?"
                f"q={quote(query)}"
                "&hl=ko"
                "&gl=KR"
                "&ceid=KR:ko"
            )

            request = urllib.request.Request(
                rss_url,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/rss+xml, application/xml, text/xml",
                },
            )

            with urllib.request.urlopen(
                request,
                timeout=10,
            ) as response:
                xml_data = response.read()

            root = ET.fromstring(xml_data)
            count = 0

            for item in root.findall(".//item"):
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                pub_date = item.findtext("pubDate", "").strip()

                if not title or not link:
                    continue

                # X는 날짜가 확인되면 2026년 자료만 표시
                # 날짜가 없는 자료는 일단 표시
                if sub_category == "X" and pub_date:
                    try:
                        parsed_date = parsedate_to_datetime(pub_date)
                        if parsed_date.year != CURRENT_YEAR:
                            continue
                    except Exception:
                        pass

                news_items.append(
                    {
                        "title": title,
                        "url": link,
                        "category": "SNS",
                        "sub_category": sub_category,
                        "date": pub_date,
                        "source": f"출처: AGF Korea {sub_category}",
                    }
                )

                count += 1

            print(
                f"[SNS RSS] {sub_category} "
                f"가져온 항목 수: {count}"
            )

        except Exception as e:
            print(
                f"[SNS RSS] {sub_category} 처리 실패:",
                repr(e),
            )

    print(
        f"[SNS RSS] 최종 SNS 항목 수: "
        f"{len(news_items)}"
    )

    return news_items


def fetch_public_news():
    page_data = [
        {
            "title": "AGF 2026 게스트 · 성우",
            "url": "https://www.agfkorea.com/stage?idx=1",
            "sub_category": "게스트",
        },
        {
            "title": "AGF 2026 참가사",
            "url": "https://www.agfkorea.com/information",
            "sub_category": "참가사",
        },
    ]

    news_items = []

    for item in page_data:
        available = False

        try:
            request = urllib.request.Request(
                item["url"],
                headers={"User-Agent": "Mozilla/5.0"},
            )

            with urllib.request.urlopen(
                request,
                timeout=10,
            ) as response:
                html = response.read().decode(
                    "utf-8",
                    errors="ignore",
                )

            if "Coming soon" not in html:
                available = True

        except Exception as e:
            print(
                f"{item['sub_category']} 공식 페이지 확인 실패:",
                e,
            )

        news_items.append(
            {
                "title": item["title"],
                "url": item["url"],
                "category": "공개",
                "sub_category": item["sub_category"],
                "source": "출처: AGF Korea",
                "description": (
                    "공식 안내가 공개되었습니다. 자세한 내용은 공식 페이지에서 확인하세요."
                    if available
                    else "공식 안내가 아직 공개되지 않았습니다."
                ),
            }
        )

    return news_items


def fetch_all_news():
    all_items = []

    try:
        all_items.extend(fetch_agf_news())
    except Exception as e:
        print("공식 뉴스 처리 실패:", e)

    try:
        all_items.extend(fetch_sns_news())
    except Exception as e:
        print("SNS 뉴스 처리 실패:", e)

    try:
        all_items.extend(fetch_public_news())
    except Exception as e:
        print("공개 정보 처리 실패:", e)

    # ==============================
    # 중복 뉴스 제거
    # URL + 제목 기준
    # ==============================
    unique_items = []
    seen_urls = set()
    seen_titles = set()

    for item in all_items:
        url = str(item.get("url", "")).strip()
        title = str(item.get("title", "")).strip()

        normalized_title = re.sub(
            r"\s+",
            " ",
            title,
        ).strip().lower()

        if url and url in seen_urls:
            continue

        if normalized_title and normalized_title in seen_titles:
            continue

        if url:
            seen_urls.add(url)

        if normalized_title:
            seen_titles.add(normalized_title)

        unique_items.append(item)

    print(
        f"[뉴스] 전체 {len(all_items)}개 → "
        f"중복 제거 후 {len(unique_items)}개"
    )

    return unique_items


def main(page: ft.Page):
    saved = False
    news_content = None
    seen_news = []
    notifications_enabled = True
    news_initialized = False

    news_category = "SNS"
    news_sub_category = "X"
    all_news_items = []
    current_language = "한국어"
    current_index = 0

    save_file = Path(__file__).with_name("agf_settings.json")

    # 기존 저장값 불러오기
    if save_file.exists():
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
            current_language = settings.get(
                "language",
                "한국어",
            )

            if current_language not in [
                "한국어",
                "English",
                "日本語",
            ]:
                current_language = "한국어"

        except (json.JSONDecodeError, OSError):
            saved = False
            seen_news = []
            notifications_enabled = True
            news_initialized = False
            current_language = "한국어"

    page.bgcolor = "#FFFFFF"
    page.padding = 0

    TRANSLATIONS = {
        "한국어": {
            "app_title": "AGF 2026 정보",
            "home": "홈",
            "news": "뉴스",
            "stage": "스테이지",
            "booth": "부스",
            "settings": "설정",
            "settings_title": "앱 설정",
            "notification": "알림",
            "auto_news": "새소식 자동 확인",
            "auto_news_desc": "AGF 2026의 새로운 소식을 자동으로 확인합니다.",
            "language": "언어",
            "app_info": "앱 정보",
            "version": "버전",
            "beta_contact": "테스트버전 문의",
            "beta_contact_desc": "베타 테스트 중 오류나 의견을 알려주세요.",
            "unofficial_notice": "비공식 팬메이드 앱",
            "unofficial_notice_desc": "본 앱은 AGF 2026 조직위원회 및 AGF Korea와 공식적인 제휴·운영 관계가 없습니다.",
            "agf_news": "AGF 뉴스",
            "refresh": "새로고침",
            "notice": "공지",
            "event_news": "행사소식",
            "sns": "SNS",
            "public": "공개",
            "instagram": "Instagram",
            "guest": "게스트",
            "participant": "참가사",
            "notification_alert": "AGF 알림",
            "notification_on": "새소식 자동 확인: ON",
            "notification_off": "새소식 자동 확인: OFF",
            "notification_desc": "새 공지가 올라오면 뉴스 화면에서 확인할 수 있습니다.",
            "confirm": "확인",
            "menu": "메뉴",
            "previous": "이전",
            "next": "다음",
            "latest_sns": "SNS 최신 소식",
            "view_all": "전체보기",
            "sns_loading": "SNS 소식을 불러오는 중...",
            "sns_empty": "새로운 SNS 소식이 없습니다.",
            "sns_error": "SNS 소식을 불러오지 못했습니다.",
            "ticket": "티켓 예매",
            "ticket_desc": "AGF 2026 티켓을 예매하세요.",
            "sponsor": "메인 스폰서 & 스폰서",
            "sponsor_desc": "AGF 2026의 메인 스폰서와 참가 스폰서를 확인하세요.",
            "sponsor_empty": "스폰서 정보 공개 후 업데이트 예정",
            "guest_card": "게스트",
            "guest_desc": "AGF 2026 공식 게스트 정보를 확인하세요.",
            "guest_empty": "게스트 정보 공개 후 업데이트 예정",
            "stage_card": "스테이지",
            "stage_desc": "AGF 2026 스테이지 일정을 확인하세요.",
            "stage_empty": "스테이지 정보 공개 후 업데이트 예정",
            "home_back": "홈으로",
            "event_schedule": "행사 일정",
            "venue_info": "행사장 안내",
            "event_info": "행사 정보",
            "event_guide": "행사 안내",
            "drawer_event_schedule": "행사 일정",
            "drawer_venue": "행사장 안내",
            "drawer_event_info": "행사 정보",
            "drawer_official_channel": "공식 채널",
            "official_channel": "공식 채널",
            "schedule_date_1": "2026년 12월 4일(금)",
            "schedule_date_2": "2026년 12월 5일(토)",
            "schedule_date_3": "2026년 12월 6일(일)",
            "venue_pending": "행사장 정보는 공식 자료가 공개되면 업데이트할 예정입니다.",
            "event_name": "Anime × Game Festival",
            "open_original": "원문 열기",
            "fanmade_short": "비공식 팬메이드",
            "source_official": "출처: AGF Korea",
            "source_x": "출처: AGF Korea X",
            "source_instagram": "출처: AGF Korea Instagram",
            "public_guest_title": "AGF 2026 게스트 · 성우",
            "public_participant_title": "AGF 2026 참가사",
            "public_pending_desc": "공식 안내가 아직 공개되지 않았습니다.",
            "public_available_desc": "공식 안내가 공개되었습니다. 자세한 내용은 공식 페이지에서 확인하세요.",
            "dday_progress": "행사 진행 중",
            "dday_finished": "행사 종료",
            "dday_preparing": "일정 준비 중",
            "dday_today": "오늘 {title} 시작!",
            "event_start_text": "{year}년 {month}월 {day}일({weekday}) 시작",
            "event_range_text": "{year}년 {start_month}월 {start_day}일({start_weekday}) ~ {end_month}월 {end_day}일({end_weekday})",
            "stage_schedule_pending": "스테이지 일정 준비 중",
            "stage_label": "{name} 스테이지",
            "time_label": "시간",
            "guest_label": "게스트",
            "booth_prefix": "부스",
            "booth_number_label": "부스 번호",
            "guest_update_footer": "※ 실제 게스트 정보 공개 후 출연 정보를 업데이트합니다.",
            "beta_dialog_title": "🧪 AGF 2026 정보 베타 테스트",
            "beta_dialog_message": "본 웹사이트는 AGF 공식 웹사이트가 아닌 비공식 팬메이드 웹사이트입니다.\n\n현재 이 웹사이트는 베타 테스트 버전입니다.\n\n일부 기능이나 정보가 변경되거나 오류가 발생할 수 있습니다.\n\n불편사항이나 오류는 「테스트버전 문의」를 통해 알려주세요.",
            "new_update": "새소식",
            "official_homepage": "공식 홈페이지",
            "official_x": "공식 X",
            "official_instagram": "공식 Instagram",
            "stage_guest": "AGF 2026 공식 게스트",
            "schedule_empty": "출연 일정 정보가 없습니다.",
            "guest_intro": "게스트 소개",
            "stage_appearances": "출연 스테이지",
            "stage_image_loading": "스테이지 이미지 준비 중",
            "stage_title": "AGF 스테이지",
            "stage_desc_main": "스테이지와 날짜를 선택해 일정을 확인하세요.",
            "booth_title": "AGF 부스",
            "booth_desc": "참가사 · 부스 · 배치도",
            "booth_intro": "공식 참가사와 부스 정보가 공개되면 이곳에서 확인할 수 있습니다.",
            "participant_search": "참가사 검색",
            "participant_info": "참가사 정보",
            "participant_empty": "공식 참가사 정보가 아직 공개되지 않았습니다.",
            "search_empty": "검색 결과가 없습니다.",
            "booth_map": "부스 & 배치도",
            "booth_map_desc": "부스 번호와 참가사를 확인할 수 있습니다.",
            "booth_list": "부스 목록",
            "booth_empty": "공식 참가사 및 부스 정보가 아직 공개되지 않았습니다.",
            "booth_update": "※ 실제 배치도와 참가사 정보 공개 후 업데이트됩니다.",
            "booth_number": "부스 번호",
            "official_update_pending": "참가사 상세 정보는 공식 자료 공개 후 업데이트할 예정입니다.",
            "map_load_error": "배치도 이미지를 불러오지 못했습니다.",
            "map_pending": "AGF 2026 부스 배치도",
            "map_update_pending": "실제 배치도 공개 후 업데이트 예정",
            "beta_test": "베타 테스트",
            "beta_test_done": "1.0.0 · 베타 테스트",
            "close": "닫기",
            "official_page": "공식 페이지 확인",
            "loading_notice": "공식 공지를 확인하는 중...",
            "no_news_title": "새로운 소식이 없습니다.",
            "no_news_desc": "현재 선택한 카테고리에 등록된 소식이 없습니다.",
        },
        "English": {
            "app_title": "AGF 2026 Info",
            "home": "Home",
            "news": "News",
            "stage": "Stage",
            "booth": "Booth",
            "settings": "Settings",
            "settings_title": "App Settings",
            "notification": "Notifications",
            "auto_news": "Check for new updates",
            "auto_news_desc": "Automatically check for new AGF 2026 updates.",
            "language": "Language",
            "app_info": "App Info",
            "version": "Version",
            "beta_contact": "Beta Test Feedback",
            "beta_contact_desc": "Report bugs or share feedback during beta testing.",
            "unofficial_notice": "Unofficial Fan-Made App",
            "unofficial_notice_desc": "This app is not officially affiliated with or operated by the AGF 2026 Organizing Committee or AGF Korea.",
            "agf_news": "AGF News",
            "refresh": "Refresh",
            "notice": "Notices",
            "event_news": "Event News",
            "sns": "SNS",
            "public": "Public",
            "instagram": "Instagram",
            "guest": "Guests",
            "participant": "Participants",
            "notification_alert": "AGF Notifications",
            "notification_on": "Check for new updates: ON",
            "notification_off": "Check for new updates: OFF",
            "notification_desc": "New notices can be checked on the News screen.",
            "confirm": "OK",
            "menu": "Menu",
            "previous": "Previous",
            "next": "Next",
            "latest_sns": "Latest SNS Updates",
            "view_all": "View All",
            "sns_loading": "Loading SNS updates...",
            "sns_empty": "No new SNS updates.",
            "sns_error": "Failed to load SNS updates.",
            "ticket": "Tickets",
            "ticket_desc": "Get your AGF 2026 tickets.",
            "sponsor": "Main Sponsors & Sponsors",
            "sponsor_desc": "Check the main sponsors and participating sponsors of AGF 2026.",
            "sponsor_empty": "To be updated after sponsor information is released",
            "guest_card": "Guests",
            "guest_desc": "Check the official AGF 2026 guest information.",
            "guest_empty": "To be updated after guest information is released",
            "stage_card": "Stage",
            "stage_desc": "Check the AGF 2026 stage schedule.",
            "stage_empty": "To be updated after stage information is released",
            "home_back": "Home",
            "event_schedule": "Event Schedule",
            "venue_info": "Venue Information",
            "event_info": "Event Information",
            "event_guide": "Event Guide",
            "drawer_event_schedule": "Event Schedule",
            "drawer_venue": "Venue Information",
            "drawer_event_info": "Event Information",
            "drawer_official_channel": "Official Channels",
            "official_channel": "Official Channels",
            "schedule_date_1": "December 4, 2026 (Fri)",
            "schedule_date_2": "December 5, 2026 (Sat)",
            "schedule_date_3": "December 6, 2026 (Sun)",
            "venue_pending": "Venue information will be updated after official information is released.",
            "event_name": "Anime × Game Festival",
            "open_original": "Open Original",
            "fanmade_short": "Unofficial Fan-Made",
            "source_official": "Source: AGF Korea",
            "source_x": "Source: AGF Korea X",
            "source_instagram": "Source: AGF Korea Instagram",
            "public_guest_title": "AGF 2026 Guests · Voice Actors",
            "public_participant_title": "AGF 2026 Participants",
            "public_pending_desc": "Official information has not been released yet.",
            "public_available_desc": "Official information has been released. Please check the official page for details.",
            "dday_progress": "Event in Progress",
            "dday_finished": "Event Ended",
            "dday_preparing": "Schedule Preparing",
            "dday_today": "{title} starts today!",
            "event_start_text": "{month_name} {day}, {year} ({weekday}) starts",
            "event_range_text": "{start_month} {start_day}, {year} ({start_weekday}) ~ {end_month} {end_day}, {year} ({end_weekday})",
            "stage_schedule_pending": "Stage schedule is being prepared",
            "stage_label": "{name} Stage",
            "time_label": "Time",
            "guest_label": "Guest",
            "booth_prefix": "Booth",
            "booth_number_label": "Booth Number",
            "guest_update_footer": "※ Guest appearance information will be updated after the official announcement.",
            "beta_dialog_title": "🧪 AGF 2026 Info Beta Test",
            "beta_dialog_message": "This website is an unofficial fan-made website and is not the official AGF website.\n\nThis website is currently in beta testing.\n\nSome features or information may change, and errors may occur.\n\nPlease report issues or feedback through Beta Test Feedback.",
            "new_update": "New Update",
            "official_homepage": "Official Website",
            "official_x": "Official X",
            "official_instagram": "Official Instagram",
            "stage_guest": "Official AGF 2026 Guest",
            "schedule_empty": "No appearance schedule information.",
            "guest_intro": "Guest Introduction",
            "stage_appearances": "Stage Appearances",
            "stage_image_loading": "Stage image is being prepared",
            "stage_title": "AGF Stage",
            "stage_desc_main": "Select a stage and date to view the schedule.",
            "booth_title": "AGF Booth",
            "booth_desc": "Participants · Booths · Floor Map",
            "booth_intro": "Participant and booth information will be available here once officially released.",
            "participant_search": "Search participants",
            "participant_info": "Participant Information",
            "participant_empty": "Official participant information has not been released yet.",
            "search_empty": "No search results.",
            "booth_map": "Booths & Floor Map",
            "booth_map_desc": "Check booth numbers and participants.",
            "booth_list": "Booth List",
            "booth_empty": "Official participant and booth information has not been released yet.",
            "booth_update": "※ The actual floor map and participant information will be updated after official release.",
            "booth_number": "Booth Number",
            "official_update_pending": "Participant details will be updated after official information is released.",
            "map_load_error": "Failed to load the floor map.",
            "map_pending": "AGF 2026 Floor Map",
            "map_update_pending": "To be updated after the actual floor map is released",
            "beta_test": "Beta Test",
            "beta_test_done": "1.0.0 · Beta Test",
            "close": "Close",
            "official_page": "View Official Page",
            "loading_notice": "Checking official notices...",
            "no_news_title": "No new updates.",
            "no_news_desc": "There are no updates in the selected category.",
        },
        "日本語": {
            "app_title": "AGF 2026 情報",
            "home": "ホーム",
            "news": "ニュース",
            "stage": "ステージ",
            "booth": "ブース",
            "settings": "設定",
            "settings_title": "アプリ設定",
            "notification": "通知",
            "auto_news": "新着情報を自動確認",
            "auto_news_desc": "AGF 2026の新しい情報を自動で確認します。",
            "language": "言語",
            "app_info": "アプリ情報",
            "version": "バージョン",
            "beta_contact": "ベータ版のお問い合わせ",
            "beta_contact_desc": "ベータテスト中の不具合やご意見をお知らせください。",
            "unofficial_notice": "非公式ファンメイドアプリ",
            "unofficial_notice_desc": "本アプリはAGF 2026実行委員会およびAGF Koreaの公式な提携・運営によるものではありません。",
            "agf_news": "AGF ニュース",
            "refresh": "更新",
            "notice": "お知らせ",
            "event_news": "イベント情報",
            "sns": "SNS",
            "public": "公開",
            "instagram": "Instagram",
            "guest": "ゲスト",
            "participant": "参加者",
            "notification_alert": "AGF 通知",
            "notification_on": "新着情報を自動確認: ON",
            "notification_off": "新着情報を自動確認: OFF",
            "notification_desc": "新しいお知らせはニュース画面で確認できます。",
            "confirm": "確認",
            "menu": "メニュー",
            "previous": "前へ",
            "next": "次へ",
            "latest_sns": "SNS 最新情報",
            "view_all": "すべて見る",
            "sns_loading": "SNS情報を読み込んでいます...",
            "sns_empty": "新しいSNS情報はありません。",
            "sns_error": "SNS情報を読み込めませんでした。",
            "ticket": "チケット予約",
            "ticket_desc": "AGF 2026のチケットを予約してください。",
            "sponsor": "メインスポンサー＆スポンサー",
            "sponsor_desc": "AGF 2026のメインスポンサーと参加スポンサーを確認してください。",
            "sponsor_empty": "スポンサー情報公開後に更新予定",
            "guest_card": "ゲスト",
            "guest_desc": "AGF 2026公式ゲスト情報を確認してください。",
            "guest_empty": "ゲスト情報公開後に更新予定",
            "stage_card": "ステージ",
            "stage_desc": "AGF 2026のステージスケジュールを確認してください。",
            "stage_empty": "ステージ情報公開後に更新予定",
            "home_back": "ホーム",
            "event_schedule": "イベント日程",
            "venue_info": "会場案内",
            "event_info": "イベント情報",
            "event_guide": "イベント案内",
            "drawer_event_schedule": "イベント日程",
            "drawer_venue": "会場案内",
            "drawer_event_info": "イベント情報",
            "drawer_official_channel": "公式チャンネル",
            "official_channel": "公式チャンネル",
            "schedule_date_1": "2026年12月4日(金)",
            "schedule_date_2": "2026年12月5日(土)",
            "schedule_date_3": "2026年12月6日(日)",
            "venue_pending": "会場情報は公式資料が公開され次第、更新する予定です。",
            "event_name": "Anime × Game Festival",
            "open_original": "原文を開く",
            "fanmade_short": "非公式ファンメイド",
            "source_official": "出典: AGF Korea",
            "source_x": "出典: AGF Korea X",
            "source_instagram": "出典: AGF Korea Instagram",
            "public_guest_title": "AGF 2026 ゲスト・声優",
            "public_participant_title": "AGF 2026 参加者",
            "public_pending_desc": "公式情報はまだ公開されていません。",
            "public_available_desc": "公式情報が公開されました。詳しくは公式ページをご確認ください。",
            "dday_progress": "イベント開催中",
            "dday_finished": "イベント終了",
            "dday_preparing": "日程準備中",
            "dday_today": "本日、{title}が開始します！",
            "event_start_text": "{year}年{month}月{day}日({weekday}) 開始",
            "event_range_text": "{year}年{start_month}月{start_day}日({start_weekday}) ～ {end_month}月{end_day}日({end_weekday})",
            "stage_schedule_pending": "ステージ日程を準備中です",
            "stage_label": "{name} ステージ",
            "time_label": "時間",
            "guest_label": "ゲスト",
            "booth_prefix": "ブース",
            "booth_number_label": "ブース番号",
            "guest_update_footer": "※ 公式ゲスト情報公開後に出演情報を更新します。",
            "beta_dialog_title": "🧪 AGF 2026 情報 ベータテスト",
            "beta_dialog_message": "本ウェブサイトはAGF公式ウェブサイトではない非公式ファンメイドウェブサイトです。\n\n現在、本ウェブサイトはベータテスト版です。\n\n一部の機能や情報が変更されたり、エラーが発生したりする場合があります。\n\n不具合やご意見は「ベータ版のお問い合わせ」からお知らせください。",
            "new_update": "新着情報",
            "official_homepage": "公式ウェブサイト",
            "official_x": "公式 X",
            "official_instagram": "公式 Instagram",
            "stage_guest": "AGF 2026公式ゲスト",
            "schedule_empty": "出演スケジュール情報はありません。",
            "guest_intro": "ゲスト紹介",
            "stage_appearances": "出演ステージ",
            "stage_image_loading": "ステージ画像を準備中",
            "stage_title": "AGF ステージ",
            "stage_desc_main": "ステージと日付を選択してスケジュールを確認してください。",
            "booth_title": "AGF ブース",
            "booth_desc": "参加者・ブース・会場マップ",
            "booth_intro": "公式参加者とブース情報が公開されると、こちらで確認できます。",
            "participant_search": "参加者を検索",
            "participant_info": "参加者情報",
            "participant_empty": "公式参加者情報はまだ公開されていません。",
            "search_empty": "検索結果はありません。",
            "booth_map": "ブース＆会場マップ",
            "booth_map_desc": "ブース番号と参加者を確認できます。",
            "booth_list": "ブース一覧",
            "booth_empty": "公式参加者およびブース情報はまだ公開されていません。",
            "booth_update": "※ 実際の会場マップと参加者情報は公式公開後に更新します。",
            "booth_number": "ブース番号",
            "official_update_pending": "参加者の詳細情報は公式資料公開後に更新します。",
            "map_load_error": "会場マップを読み込めませんでした。",
            "map_pending": "AGF 2026 会場マップ",
            "map_update_pending": "実際の会場マップ公開後に更新予定",
            "beta_test": "ベータテスト",
            "beta_test_done": "1.0.0 · ベータテスト",
            "close": "閉じる",
            "official_page": "公式ページを確認",
            "loading_notice": "公式のお知らせを確認しています...",
            "no_news_title": "新しい情報はありません。",
            "no_news_desc": "現在選択したカテゴリーに登録された情報はありません。",
        },
    }

    page.title = TRANSLATIONS.get(
        current_language,
        TRANSLATIONS["한국어"],
    )["app_title"]

    def t(key):
        return TRANSLATIONS.get(
            current_language,
            TRANSLATIONS["한국어"],
        ).get(
            key,
            key,
        )

    # ==============================
    # 설정 저장
    # ==============================
    def save_settings():
        settings = {
            "saved": saved,
            "seen_news": seen_news,
            "notifications_enabled": notifications_enabled,
            "news_initialized": news_initialized,
            "language": current_language,
        }
        save_file.write_text(
            json.dumps(
                settings,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    # ==============================
    # Windows 팝업 알림
    # ==============================
    def show_windows_notification(title, message, url=None):
        if Notification is None:
            print(
                "웹 서버 환경에서는 Windows 알림을 건너뜁니다."
            )
            return

        try:
            notification = Notification(
                app_id=AGF_TITLE,
                title=title,
                msg=message,
            )

            if url:
                notification.add_actions(
                    label=t("open_original"),
                    launch=urljoin(
                        "https://www.agfkorea.com",
                        url,
                    ),
                )

            notification.show()
            print("Windows 알림 표시:", title)

        except Exception as e:
            print("Windows 알림 실패:", e)

    def notification_clicked(e):
        status = (
            t("notification_on")
            if notifications_enabled
            else t("notification_off")
        )

        dialog = ft.AlertDialog(
            title=ft.Text(t("notification_alert")),
            content=ft.Text(
                status
                + "\n\n"
                + t("notification_desc")
            ),
            actions=[
                ft.TextButton(
                    t("confirm"),
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

        weekday_names_by_language = {
            "한국어": [
                "월", "화", "수", "목", "금", "토", "일"
            ],
            "English": [
                "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"
            ],
            "日本語": [
                "月", "火", "水", "木", "金", "土", "日"
            ],
        }

        weekday_names = weekday_names_by_language.get(
            current_language,
            weekday_names_by_language["한국어"],
        )

        start_weekday = weekday_names[event_start.weekday()]
        end_weekday = weekday_names[event_end.weekday()]

        if current_language == "English":
            month_names = [
                "January", "February", "March", "April",
                "May", "June", "July", "August",
                "September", "October", "November", "December",
            ]

            start_date_values = {
                "month_name": month_names[event_start.month - 1],
                "day": event_start.day,
                "year": CURRENT_YEAR,
                "weekday": start_weekday,
                "month": event_start.month,
                "start_month": month_names[event_start.month - 1],
                "start_day": event_start.day,
                "start_weekday": start_weekday,
                "end_month": month_names[event_end.month - 1],
                "end_day": event_end.day,
                "end_weekday": end_weekday,
            }
        else:
            start_date_values = {
                "month": event_start.month,
                "day": event_start.day,
                "year": CURRENT_YEAR,
                "weekday": start_weekday,
                "start_month": event_start.month,
                "start_day": event_start.day,
                "start_weekday": start_weekday,
                "end_month": event_end.month,
                "end_day": event_end.day,
                "end_weekday": end_weekday,
            }

        if days_left > 0:
            dday_text = f"D-{days_left}"
            date_text = t("event_start_text").format(
                **start_date_values
            )
        elif days_left == 0:
            dday_text = "D-DAY"
            date_text = t("dday_today").format(
                title=t("app_title")
            )
        elif today <= event_end:
            dday_text = t("dday_progress")
            date_text = t("event_range_text").format(
                **start_date_values
            )
        else:
            dday_text = t("dday_finished")
            date_text = t("event_range_text").format(
                **start_date_values
            )
    else:
        dday_text = t("dday_preparing")
        date_text = f"{CURRENT_YEAR} {t('dday_preparing')}"

    async def menu_clicked(e):
        await page.show_end_drawer()

    def apply_language(language):
        nonlocal current_language

        current_language = language
        save_settings()

        page.title = t("app_title")
        page.end_drawer = build_drawer()

        navigation.destinations[0].label = t("home")
        navigation.destinations[1].label = t("news")
        navigation.destinations[2].label = t("stage")
        navigation.destinations[3].label = t("booth")
        navigation.destinations[4].label = t("settings")

        set_appbar(current_index)

        if current_index == 0:
            content_area.content = build_home_view()
            refresh_home_sns()
        elif current_index == 1:
            change_page(index=1)
        elif current_index == 2:
            change_page(index=2)
        elif current_index == 3:
            change_page(index=3)
        elif current_index == 4:
            content_area.content = more_view()

        page.update()

    def get_language_code():
        language_codes = {
            "한국어": "KR",
            "English": "EN",
            "日本語": "JP",
        }

        return language_codes.get(
            current_language,
            "KR",
        )

    def build_language_button():
        return ft.Container(
            width=48,
            height=48,
            alignment=ft.Alignment.CENTER,
            ink=True,
            tooltip=t("language"),
            on_click=language_button_clicked,
            content=ft.Text(
                get_language_code(),
                size=14,
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.CENTER,
            ),
        )

    def language_button_clicked(e):
        def select_language(language):
            page.pop_dialog()
            apply_language(language)

        dialog = ft.AlertDialog(
            title=ft.Text(
                t("language"),
                weight=ft.FontWeight.BOLD,
            ),
            content=ft.Column(
                tight=True,
                spacing=4,
                controls=[
                    ft.TextButton(
                        "한국어",
                        on_click=lambda e: select_language("한국어"),
                    ),
                    ft.TextButton(
                        "English",
                        on_click=lambda e: select_language("English"),
                    ),
                    ft.TextButton(
                        "日本語",
                        on_click=lambda e: select_language("日本語"),
                    ),
                ],
            ),
            actions=[
                ft.TextButton(
                    t("close"),
                    on_click=lambda e: page.pop_dialog(),
                ),
            ],
        )

        page.show_dialog(dialog)

    def set_appbar(index):
        titles = {
            1: t("news"),
            2: t("stage"),
            3: t("booth"),
            4: t("settings"),
        }

        if index == 0:
            page.appbar = ft.AppBar(
                title=ft.Column(
                    spacing=0,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(
                            t("app_title"),
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
                    build_language_button(),
                    ft.IconButton(
                        icon=ft.Icons.NOTIFICATIONS_OUTLINED,
                        tooltip=t("notification"),
                        on_click=notification_clicked,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.MENU,
                        tooltip=t("menu"),
                        on_click=menu_clicked,
                    ),
                ],
            )
        else:
            page.appbar = ft.AppBar(
                leading=ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    tooltip=t("home_back"),
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
                    build_language_button(),
                    ft.IconButton(
                        icon=ft.Icons.NOTIFICATIONS_OUTLINED,
                        tooltip=t("notification"),
                        on_click=notification_clicked,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.MENU,
                        tooltip=t("menu"),
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
                    t("confirm"),
                    on_click=lambda e: page.pop_dialog(),
                ),
            ],
        )

        page.show_dialog(dialog)

    async def schedule_clicked(e):
        await show_drawer_dialog(
            t("event_schedule"),
            "AGF 2026\n\n"
            f"{t('schedule_date_1')}\n"
            f"{t('schedule_date_2')}\n"
            f"{t('schedule_date_3')}",
        )

    async def venue_clicked(e):
        await show_drawer_dialog(
            t("venue_info"),
            t("venue_pending"),
        )

    async def event_info_clicked(e):
        await show_drawer_dialog(
            t("event_info"),
            "AGF 2026\n\n"
            + t("event_name"),
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

    def build_drawer():
        return ft.NavigationDrawer(
            width=320,
            controls=[
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
                                t("unofficial_notice"),
                                size=24,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                t("unofficial_notice_desc"),
                                size=13,
                                color="#666666",
                            ),
                        ],
                    ),
                ),
                ft.Divider(),
                ft.Container(
                    padding=ft.Padding(
                        left=24,
                        top=8,
                        right=20,
                        bottom=4,
                    ),
                    content=ft.Text(
                        t("event_guide"),
                        size=13,
                        color="#777777",
                        weight=ft.FontWeight.BOLD,
                    ),
                ),
                ft.ListTile(
                    leading=ft.Icon(
                        ft.Icons.CALENDAR_MONTH_OUTLINED,
                    ),
                    title=ft.Text(
                        t("drawer_event_schedule"),
                    ),
                    trailing=ft.Icon(
                        ft.Icons.CHEVRON_RIGHT,
                    ),
                    on_click=schedule_clicked,
                ),
                ft.ListTile(
                    leading=ft.Icon(
                        ft.Icons.LOCATION_ON_OUTLINED,
                    ),
                    title=ft.Text(
                        t("drawer_venue"),
                    ),
                    trailing=ft.Icon(
                        ft.Icons.CHEVRON_RIGHT,
                    ),
                    on_click=venue_clicked,
                ),
                ft.ListTile(
                    leading=ft.Icon(
                        ft.Icons.INFO_OUTLINED,
                    ),
                    title=ft.Text(
                        t("drawer_event_info"),
                    ),
                    trailing=ft.Icon(
                        ft.Icons.CHEVRON_RIGHT,
                    ),
                    on_click=event_info_clicked,
                ),
                ft.Divider(),
                ft.Container(
                    padding=ft.Padding(
                        left=24,
                        top=8,
                        right=20,
                        bottom=4,
                    ),
                    content=ft.Text(
                        t("drawer_official_channel"),
                        size=13,
                        color="#777777",
                        weight=ft.FontWeight.BOLD,
                    ),
                ),
                ft.ListTile(
                    leading=ft.Icon(
                        ft.Icons.LANGUAGE,
                    ),
                    title=ft.Text(
                        t("official_homepage"),
                    ),
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
                    title=ft.Text(
                        t("official_x"),
                    ),
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
                    title=ft.Text(
                        t("official_instagram"),
                    ),
                    url="https://www.instagram.com/agf_korea/",
                    trailing=ft.Icon(
                        ft.Icons.OPEN_IN_NEW,
                    ),
                    on_click=official_instagram_clicked,
                ),
                ft.ListTile(
                    leading=ft.Icon(
                        ft.Icons.HELP_OUTLINE,
                    ),
                    title=ft.Text(
                        t("beta_contact"),
                    ),
                    url="https://naver.me/G6RXO3S9",
                    trailing=ft.Icon(
                        ft.Icons.OPEN_IN_NEW,
                    ),
                ),
            ],
        )

    page.end_drawer = build_drawer()
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
                ft.Container(
                    padding=ft.Padding(
                        left=20,
                        right=20,
                        top=20,
                        bottom=16,
                    ),
                    content=ft.Text(
                        t("settings_title"),
                        size=26,
                        weight=ft.FontWeight.BOLD,
                    ),
                ),
                ft.Container(
                    padding=ft.Padding(
                        left=20,
                        right=20,
                        top=8,
                        bottom=8,
                    ),
                    content=ft.Text(
                        t("notification"),
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
                            t("auto_news"),
                            size=16,
                        ),
                        subtitle=ft.Text(
                            t("auto_news_desc"),
                            size=13,
                        ),
                        trailing=ft.Switch(
                            value=notifications_enabled,
                            on_change=notification_changed,
                        ),
                    ),
                ),
                ft.Container(
                    padding=ft.Padding(
                        left=20,
                        right=20,
                        top=8,
                        bottom=8,
                    ),
                    content=ft.Text(
                        t("language"),
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
                    padding=ft.Padding(
                        left=16,
                        right=16,
                        top=8,
                        bottom=8,
                    ),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(
                                spacing=12,
                                controls=[
                                    ft.Icon(ft.Icons.LANGUAGE),
                                    ft.Column(
                                        spacing=2,
                                        controls=[
                                            ft.Text(
                                                t("language"),
                                                size=16,
                                            ),
                                            ft.Text(
                                                "한국어 / English / 日本語",
                                                size=13,
                                                color="#666666",
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            ft.Dropdown(
                                value=current_language,
                                width=130,
                                options=[
                                    ft.DropdownOption(
                                        key="한국어",
                                        text="한국어",
                                    ),
                                    ft.DropdownOption(
                                        key="English",
                                        text="English",
                                    ),
                                    ft.DropdownOption(
                                        key="日本語",
                                        text="日本語",
                                    ),
                                ],
                                on_select=language_changed,
                            ),
                        ],
                    ),
                ),
                ft.Container(
                    padding=ft.Padding(
                        left=20,
                        right=20,
                        top=8,
                        bottom=8,
                    ),
                    content=ft.Text(
                        t("app_info"),
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
                                leading=ft.Icon(ft.Icons.EVENT_OUTLINED),
                                title=ft.Text(
                                    t("app_title"),
                                    size=16,
                                ),
                                subtitle=ft.Text(
                                    t("fanmade_short"),
                                    size=13,
                                ),
                            ),
                            ft.Divider(height=1),
                            ft.ListTile(
                                leading=ft.Icon(ft.Icons.INFO_OUTLINED),
                                title=ft.Text(
                                    t("version"),
                                    size=16,
                                ),
                                trailing=ft.Text(
                                    t("beta_test_done"),
                                    size=14,
                                    color="#777777",
                                ),
                            ),
                            ft.ListTile(
                                leading=ft.Icon(ft.Icons.INFO_OUTLINE),
                                title=ft.Text(
                                    t("unofficial_notice"),
                                    size=16,
                                ),
                                subtitle=ft.Text(
                                    t("unofficial_notice_desc"),
                                    size=13,
                                ),
                            ),
                            ft.Divider(height=1),
                            ft.ListTile(
                                leading=ft.Icon(ft.Icons.HELP_OUTLINE),
                                title=ft.Text(
                                    t("beta_contact"),
                                    size=16,
                                ),
                                subtitle=ft.Text(
                                    t("beta_contact_desc"),
                                    size=13,
                                ),
                                trailing=ft.Icon(ft.Icons.OPEN_IN_NEW),
                                url="https://naver.me/G6RXO3S9",
                            ),
                        ],
                    ),
                ),
            ],
        )

    def language_changed(e):
        apply_language(e.control.value)

    # ==============================
    # 뉴스 카드
    # ==============================
    def get_news_title_text(item):
        if item.get("category") == "공개":
            if item.get("sub_category") == "게스트":
                return t("public_guest_title")
            if item.get("sub_category") == "참가사":
                return t("public_participant_title")

        return item.get("title", "")

    def get_news_description_text(item):
        if item.get("category") == "공개":
            description = str(item.get("description", "")).strip()

            if description == "공식 안내가 공개되었습니다. 자세한 내용은 공식 페이지에서 확인하세요.":
                return t("public_available_desc")

            if description:
                return t("public_pending_desc")

        return item.get("description", "")

    def get_news_source_text(item):
        category = item.get("category")
        sub_category = item.get("sub_category")

        if category == "공지":
            return t("source_official")

        if category == "SNS":
            if sub_category == "Instagram":
                return t("source_instagram")
            return t("source_x")

        if category == "공개":
            return t("source_official")

        return item.get("source", "")

    def build_news_card(item):
        controls = [
            ft.Text(
                get_news_title_text(item),
                size=19,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Row(
                spacing=10,
                controls=[
                    ft.Text(
                        str(item.get("date", ""))[:10].replace("-", "."),
                        size=14,
                        color="#777777",
                    ),
                    ft.Text(
                        "·",
                        size=12,
                        color="#AAAAAA",
                    ),
                    ft.Text(
                        get_news_source_text(item),
                        size=13,
                        color="#777777",
                    ),
                ],
            ),
        ]

        description_text = get_news_description_text(item)

        if description_text:
            controls.append(
                ft.Text(
                    description_text,
                    size=14,
                    color="#666666",
                )
            )

        controls.append(
            ft.Button(
                t("official_page"),
                icon=ft.Icons.OPEN_IN_NEW,
                url=item["url"],
            )
        )

        return ft.Container(
            padding=22,
            margin=ft.Margin(bottom=4),
            border_radius=16,
            bgcolor="#F5F5F5",
            content=ft.Column(
                spacing=12,
                controls=controls,
            ),
        )

    def get_filtered_news():
        if news_category == "전체":
            return all_news_items

        if news_category == "공지":
            return [
                item
                for item in all_news_items
                if item.get("category") == "공지"
            ]

        if news_category == "SNS":
            return [
                item
                for item in all_news_items
                if item.get("category") == "SNS"
                and item.get("sub_category") == news_sub_category
            ]

        if news_category == "공개":
            return [
                item
                for item in all_news_items
                if item.get("category") == "공개"
                and item.get("sub_category") == news_sub_category
            ]

        return []

    def refresh_news(e=None):
        if news_content is None:
            return

        new_items = fetch_all_news() or []

        all_news_items.clear()
        all_news_items.extend(new_items)

        news_content.controls.clear()
        filtered_items = get_filtered_news()

        def news_sort_key(item):
            news_date = str(
                item.get("date", "")
            ).strip()

            if not news_date:
                return 0

            try:
                return parsedate_to_datetime(
                    news_date
                ).timestamp()
            except Exception:
                pass

            try:
                return date.fromisoformat(
                    news_date[:10]
                ).toordinal()
            except Exception:
                pass

            try:
                return date(
                    int(news_date[:4]),
                    1,
                    1,
                ).toordinal()
            except Exception:
                pass

            return 0

        filtered_items.sort(
            key=news_sort_key,
            reverse=True,
        )

        if not filtered_items:
            news_content.controls.append(
                ft.Container(
                    padding=20,
                    border_radius=15,
                    bgcolor="#F5F5F5",
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                t("no_news_title"),
                                size=18,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                t("no_news_desc"),
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

    # ==============================
    # 하단 메뉴
    # ==============================
    navigation = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.HOME_OUTLINED,
                selected_icon=ft.Icons.HOME,
                label=t("home"),
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.NEWSPAPER_OUTLINED,
                selected_icon=ft.Icons.NEWSPAPER,
                label=t("news"),
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.MIC_OUTLINED,
                selected_icon=ft.Icons.MIC,
                label=t("stage"),
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.STORE_OUTLINED,
                selected_icon=ft.Icons.STORE,
                label=t("booth"),
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icons.SETTINGS,
                label=t("settings"),
            ),
        ],
    )

    # ==============================
    # 홈 화면 임시 UI
    # ==============================
    home_sns_content = ft.Column(
        spacing=8,
        controls=[
            ft.Text(
                t("sns_loading"),
                size=14,
                color="#666666",
            )
        ],
    )

    def refresh_home_sns():
        try:
            sns_items = fetch_sns_news() or []

            def sns_sort_key(item):
                try:
                    return parsedate_to_datetime(
                        item.get("date", "")
                    )
                except Exception:
                    return parsedate_to_datetime(
                        "Thu, 01 Jan 1970 00:00:00 GMT"
                    )

            sns_items.sort(
                key=sns_sort_key,
                reverse=True,
            )

            home_sns_content.controls.clear()

            if not sns_items:
                home_sns_content.controls.append(
                    ft.Text(
                        t("sns_empty"),
                        size=14,
                        color="#666666",
                    )
                )
            else:
                for item in sns_items[:3]:
                    home_sns_content.controls.append(
                        ft.Container(
                            padding=12,
                            border_radius=10,
                            bgcolor="#F5F5F5",
                            url=item["url"],
                            content=ft.Row(
                                spacing=10,
                                controls=[
                                    ft.Container(
                                        width=58,
                                        content=ft.Text(
                                            item.get(
                                                "sub_category",
                                                "SNS",
                                            ),
                                            size=12,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                    ),
                                    ft.Text(
                                        item["title"],
                                        size=14,
                                        expand=True,
                                        max_lines=2,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                ],
                            ),
                        )
                    )

        except Exception as e:
            print(
                "홈 SNS 뉴스 처리 실패:",
                repr(e),
            )

            home_sns_content.controls.clear()
            home_sns_content.controls.append(
                ft.Text(
                    t("sns_error"),
                    size=14,
                    color="#666666",
                )
            )

        home_sns_content.update()

    def build_home_view():
        # SNS 최신 소식
        home_sns = ft.Container(
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
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text(
                                f"📱 {t('latest_sns')}",
                                size=20,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.TextButton(
                                t("view_all"),
                                on_click=lambda e: change_page(index=1),
                            ),
                        ],
                    ),
                    home_sns_content,
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
            url="https://m.ticket.melon.com/public/index.html#action",
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
                                        t("ticket"),
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        t("ticket_desc"),
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
            width=float("inf"),
            padding=24,
            border_radius=18,
            bgcolor="#F5F5F5",
            content=ft.Column(
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        f"⭐ {t('sponsor')}",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        t("sponsor_desc"),
                        size=15,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        t("sponsor_empty"),
                        size=13,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
            ),
        )

        # 게스트 카드
        guest_card = ft.Container(
            width=float("inf"),
            padding=24,
            border_radius=18,
            bgcolor="#F5F5F5",
            on_click=open_guest_news,
            content=ft.Column(
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        f"🎤 {t('guest_card')}",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        t("guest_desc"),
                        size=15,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        t("guest_empty"),
                        size=13,
                        color="#666666",
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
            ),
        )

        # 스테이지 카드
        stage_card = ft.Container(
            width=float("inf"),
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
                        f"🎤 {t('stage_card')}",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        t("stage_desc"),
                        size=15,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        t("stage_empty"),
                        size=13,
                        color="#666666",
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
            ),
        )

        # 홈 스와이프 영역
        home_page_view = ft.PageView(
            height=190,
            viewport_fraction=0.90,
            horizontal=True,
            snap=True,
            controls=[
                ft.Container(
                    width=float("inf"),
                    alignment=ft.Alignment.CENTER,
                    content=sponsor_card,
                ),
                ft.Container(
                    width=float("inf"),
                    alignment=ft.Alignment.CENTER,
                    content=guest_card,
                ),
                ft.Container(
                    width=float("inf"),
                    alignment=ft.Alignment.CENTER,
                    content=stage_card,
                ),
            ],
        )

        async def previous_home_card(e):
            current = home_page_view.selected_index

            if current > 0:
                await home_page_view.previous_page(
                    animation_duration=300,
                )
            else:
                await home_page_view.go_to_page(
                    2,
                    animation_duration=300,
                )

        async def next_home_card(e):
            current = home_page_view.selected_index

            if current < 2:
                await home_page_view.next_page(
                    animation_duration=300,
                )
            else:
                await home_page_view.go_to_page(
                    0,
                    animation_duration=300,
                )

        home_swipe_area = ft.Container(
            margin=ft.Margin(
                left=8,
                right=8,
                top=8,
                bottom=12,
            ),
            content=ft.Stack(
                controls=[
                    home_page_view,
                    ft.Container(
                        left=2,
                        top=74,
                        content=ft.IconButton(
                            icon=ft.Icons.CHEVRON_LEFT,
                            icon_size=32,
                            on_click=previous_home_card,
                        ),
                    ),
                    ft.Container(
                        right=2,
                        top=74,
                        content=ft.IconButton(
                            icon=ft.Icons.CHEVRON_RIGHT,
                            icon_size=32,
                            on_click=next_home_card,
                        ),
                    ),
                ],
            ),
        )

        return ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=0,
            controls=[
                home_sns,
                ticket_card,
                home_swipe_area,
            ],
        )

    # 뉴스 하위 카테고리 영역
    news_subcategory_area = ft.Container()
    news_tabs_control = None

    # ==============================
    # 뉴스 상단 / 하위 카테고리
    # ==============================
    def news_tab_changed(e=None, selected_index=0):
        nonlocal news_category, news_sub_category

        categories = [
            "SNS",
            "공개",
            "공지",
        ]

        if e is not None:
            selected_index = e.control.selected_index

        news_category = categories[selected_index]
        news_subcategory_area.content = None

        if news_category == "SNS":
            news_sub_category = "X"

            def sns_sub_changed(e):
                nonlocal news_sub_category

                if e.control.selected_index == 0:
                    news_sub_category = "X"
                else:
                    news_sub_category = "Instagram"

                refresh_news()

            news_subcategory_area.content = ft.Tabs(
                length=2,
                selected_index=0,
                on_change=sns_sub_changed,
                content=ft.Column(
                    controls=[
                        ft.TabBar(
                            height=48,
                            scrollable=True,
                            tab_alignment=ft.TabAlignment.START,
                            indicator_thickness=2,
                            label_text_style=ft.TextStyle(
                                size=15,
                                weight=ft.FontWeight.BOLD,
                            ),
                            label_padding=ft.Padding(
                                left=14,
                                right=14,
                                top=7,
                                bottom=7,
                            ),
                            tabs=[
                                ft.Tab(label="X"),
                                ft.Tab(label=t("instagram")),
                            ],
                        ),
                    ],
                ),
            )

        elif news_category == "공개":
            news_sub_category = "게스트"

            def public_sub_changed(e):
                nonlocal news_sub_category

                if e.control.selected_index == 0:
                    news_sub_category = "게스트"
                else:
                    news_sub_category = "참가사"

                refresh_news()

            news_subcategory_area.content = ft.Tabs(
                length=2,
                selected_index=0,
                on_change=public_sub_changed,
                content=ft.Column(
                    controls=[
                        ft.TabBar(
                            height=48,
                            scrollable=True,
                            tab_alignment=ft.TabAlignment.START,
                            indicator_thickness=2,
                            label_text_style=ft.TextStyle(
                                size=15,
                                weight=ft.FontWeight.BOLD,
                            ),
                            label_padding=ft.Padding(
                                left=14,
                                right=14,
                                top=7,
                                bottom=7,
                            ),
                            tabs=[
                                ft.Tab(label=t("guest")),
                                ft.Tab(label=t("participant")),
                            ],
                        ),
                    ],
                ),
            )

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
                                    t("no_news_title"),
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    t("no_news_desc"),
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

    # ==============================
    # 화면 전환
    # ==============================
    def change_page(e=None, index=None):
        nonlocal news_content, current_index
        nonlocal news_category, news_sub_category
        nonlocal news_tabs_control

        if index is None:
            index = e.control.selected_index

        current_index = index
        navigation.selected_index = index
        set_appbar(index)

        if index == 0:
            content_area.content = build_home_view()

        elif index == 1:
            news_content = ft.Column(
                spacing=10,
                controls=[
                    ft.Text(
                        t("loading_notice"),
                        size=14,
                    )
                ],
            )

            news_category = "SNS"
            news_sub_category = "X"

            news_tabs_control = ft.Tabs(
                length=3,
                selected_index=0,
                on_change=news_tab_changed,
                content=ft.Column(
                    controls=[
                        ft.TabBar(
                            height=58,
                            scrollable=True,
                            tab_alignment=ft.TabAlignment.START,
                            indicator_thickness=3,
                            label_text_style=ft.TextStyle(
                                size=17,
                                weight=ft.FontWeight.BOLD,
                            ),
                            label_padding=ft.Padding(
                                left=18,
                                right=18,
                                top=10,
                                bottom=10,
                            ),
                            tabs=[
                                ft.Tab(label=t("sns")),
                                ft.Tab(label=t("public")),
                                ft.Tab(label=t("notice")),
                            ],
                        ),
                    ],
                ),
            )

            news_tab_changed(selected_index=0)

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
                                    t("agf_news"),
                                    size=26,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Button(
                                    t("refresh"),
                                    icon=ft.Icons.REFRESH,
                                    on_click=refresh_news,
                                ),
                            ],
                        ),
                    ),
                    news_tabs_control,
                    news_subcategory_area,
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
                    "Red": [],
                    "Blue": [],
                },
                "12월 5일(토)": {
                    "Red": [],
                    "Blue": [],
                },
                "12월 6일(일)": {
                    "Red": [],
                    "Blue": [],
                },
            }

            guest_data = {}

            stage_date_labels = {
                "12월 4일(금)": t("schedule_date_1"),
                "12월 5일(토)": t("schedule_date_2"),
                "12월 6일(일)": t("schedule_date_3"),
            }

            def get_stage_date_label(date_name):
                return stage_date_labels.get(
                    date_name,
                    date_name,
                )

            def show_guest_detail(guest_name):
                guest = guest_data.get(
                    guest_name,
                    {
                        "name": guest_name,
                        "role": t("stage_guest"),
                        "description": t("official_update_pending"),
                        "image": None,
                    },
                )

                guest_schedule = []

                for date_name, stages in stage_data.items():
                    for stage_name, items in stages.items():
                        for item in items:
                            if item["guest"] == guest_name:
                                guest_schedule.append(
                                    {
                                        "date": get_stage_date_label(date_name),
                                        "stage": stage_name,
                                        "time": item["time"],
                                        "title": item["title"],
                                    }
                                )

                page.appbar = ft.AppBar(
                    leading=ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        tooltip=t("stage"),
                        on_click=lambda e: change_page(index=2),
                    ),
                    title=ft.Text(
                        t("guest_card"),
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
                            tooltip=t("notification"),
                            on_click=notification_clicked,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.MENU,
                            tooltip=t("menu"),
                            on_click=menu_clicked,
                        ),
                    ],
                )

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
                            t("schedule_empty"),
                            size=14,
                            color="#666666",
                        )
                    )

                content_area.content = ft.Column(
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        ft.Container(
                            padding=20,
                            content=ft.Column(
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=12,
                                controls=[
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
                                        t("stage_appearances"),
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
                                t("guest_update_footer"),
                                size=12,
                                color="#777777",
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ),
                    ],
                )

                page.update()

            def show_stage_detail(date_name, stage_name, item):
                dialog = ft.AlertDialog(
                    title=ft.Text(
                        item["title"],
                        weight=ft.FontWeight.BOLD,
                    ),
                    content=ft.Column(
                        tight=True,
                        spacing=10,
                        controls=[
                            ft.Text(f"📅 {get_stage_date_label(date_name)}"),
                            ft.Text(f"🎤 {t('stage_label').format(name=stage_name)}"),
                            ft.Text(f"🕒 {t('time_label')}: {item['time']}"),
                            ft.Text(f"👤 {t('guest_label')}: {item['guest']}"),
                        ],
                    ),
                    actions=[
                        ft.TextButton(
                            t("close"),
                            on_click=lambda e: setattr(dialog, "open", False)
                            or page.update(),
                        ),
                    ],
                )
                page.show_dialog(dialog)

            def build_stage_schedule(date_name, stage_name):
                items = stage_data.get(
                    date_name,
                    {},
                ).get(
                    stage_name,
                    [],
                )

                if not items:
                    content = ft.Container(
                        padding=30,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=8,
                            controls=[
                                ft.Icon(
                                    ft.Icons.EVENT_OUTLINED,
                                    size=45,
                                ),
                                ft.Text(
                                    t("stage_schedule_pending"),
                                    size=17,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    f"{get_stage_date_label(date_name)} · {t('stage_label').format(name=stage_name)}",
                                    size=13,
                                    color="#777777",
                                    text_align=ft.TextAlign.CENTER,
                                ),
                            ],
                        ),
                    )
                else:
                    timeline_controls = []

                    for item in items:
                        timeline_controls.append(
                            ft.Container(
                                padding=15,
                                border_radius=12,
                                bgcolor="#F5F5F5",
                                on_click=lambda e, item=item: show_stage_detail(
                                    date_name,
                                    stage_name,
                                    item,
                                ),
                                content=ft.Row(
                                    spacing=12,
                                    vertical_alignment=ft.CrossAxisAlignment.START,
                                    controls=[
                                        ft.Container(
                                            width=65,
                                            content=ft.Text(
                                                item.get("time", ""),
                                                size=14,
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                        ),
                                        ft.Container(
                                            width=3,
                                            height=65,
                                            bgcolor="#CCCCCC",
                                            border_radius=2,
                                        ),
                                        ft.Column(
                                            expand=True,
                                            spacing=4,
                                            controls=[
                                                ft.Text(
                                                    item.get("title", ""),
                                                    size=16,
                                                    weight=ft.FontWeight.BOLD,
                                                ),
                                                ft.Text(
                                                    item.get("guest", ""),
                                                    size=13,
                                                    color="#666666",
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                            )
                        )

                    content = ft.Column(
                        spacing=10,
                        scroll=ft.ScrollMode.AUTO,
                        controls=timeline_controls,
                    )

                return ft.Container(
                    expand=True,
                    padding=10,
                    border_radius=14,
                    bgcolor="#FFFFFF",
                    content=content,
                )

            stage_tabs = []

            for stage_name in ["Red", "Blue"]:
                date_tabs = []

                for date_name in stage_data.keys():
                    date_tabs.append(
                        ft.Container(
                            expand=True,
                            padding=10,
                            content=build_stage_schedule(
                                date_name,
                                stage_name,
                            ),
                        )
                    )

                stage_tabs.append(
                    ft.Container(
                        expand=True,
                        padding=10,
                        content=ft.Tabs(
                            length=3,
                            selected_index=0,
                            expand=True,
                            content=ft.Column(
                                expand=True,
                                controls=[
                                    ft.TabBar(
                                        scrollable=False,
                                        tab_alignment=ft.TabAlignment.FILL,
                                        indicator_thickness=3,
                                        tabs=[
                                            ft.Tab(label="12/4"),
                                            ft.Tab(label="12/5"),
                                            ft.Tab(label="12/6"),
                                        ],
                                    ),
                                    ft.Container(
                                        expand=True,
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
                spacing=0,
                controls=[
                    ft.Container(
                        padding=20,
                        content=ft.Column(
                            spacing=5,
                            controls=[
                                ft.Text(
                                    t("stage_title"),
                                    size=26,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    t("stage_desc_main"),
                                    size=14,
                                    color="#666666",
                                ),
                            ],
                        ),
                    ),
                    ft.Container(
                        expand=True,
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
                            expand=True,
                            content=ft.Column(
                                expand=True,
                                controls=[
                                    ft.TabBar(
                                        scrollable=False,
                                        tab_alignment=ft.TabAlignment.FILL,
                                        indicator_thickness=3,
                                        tabs=[
                                            ft.Tab(label="Red"),
                                            ft.Tab(label="Blue"),
                                        ],
                                    ),
                                    ft.Container(
                                        expand=True,
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
                        f"{t('booth_number_label')}: {item['booth']}\n\n"
                        + t("official_update_pending")
                    ),
                    actions=[
                        ft.TextButton(
                            t("confirm"),
                            on_click=lambda e: page.pop_dialog(),
                        ),
                    ],
                )
                page.show_dialog(dialog)

            search_field = ft.TextField(
                hint_text=t("participant_search"),
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
                            on_click=lambda e, item=item: show_participant_detail(item),
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
                                                f"{t('booth_prefix')} {item['booth']}",
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

                if not participants:
                    participant_list.controls.append(
                        ft.Text(
                            t("participant_empty"),
                            size=14,
                            color="#666666",
                        )
                    )
                elif not participant_list.controls:
                    participant_list.controls.append(
                        ft.Text(
                            t("search_empty"),
                            size=14,
                        )
                    )

                page.update()

            search_field.on_change = update_participants
            update_participants()

            booth_list = ft.Column(
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            )

            def show_booth_detail(item):
                dialog = ft.AlertDialog(
                    title=ft.Text(
                        f"{t('booth_prefix')} {item['booth']}",
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
                                f"{t('booth_number_label')}: {item['booth']}",
                                size=14,
                            ),
                            ft.Divider(),
                            ft.Text(
                                t("official_update_pending"),
                                size=13,
                            ),
                        ],
                    ),
                    actions=[
                        ft.TextButton(
                            t("confirm"),
                            on_click=lambda e: page.pop_dialog(),
                        ),
                    ],
                )
                page.show_dialog(dialog)

            if not participants:
                booth_list.controls.append(
                    ft.Text(
                        t("booth_empty"),
                        size=14,
                        color="#666666",
                    )
                )
            else:
                for item in participants:
                    booth_list.controls.append(
                        ft.Container(
                            padding=15,
                            border_radius=12,
                            bgcolor="#FFFFFF",
                            on_click=lambda e, item=item: show_booth_detail(item),
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
                                    t("map_load_error"),
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
                                t("map_pending"),
                                size=18,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                t("map_update_pending"),
                                size=13,
                                color="#666666",
                            ),
                        ],
                    ),
                )

            content_area.content = ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    ft.Container(
                        padding=20,
                        content=ft.Text(
                            t("booth_title"),
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
                                    t("booth_desc"),
                                    size=20,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    t("booth_intro"),
                                    size=14,
                                ),
                            ],
                        ),
                    ),
                    ft.Container(
                        expand=True,
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
                            expand=True,
                            content=ft.Column(
                                expand=True,
                                controls=[
                                    ft.TabBar(
                                        scrollable=False,
                                        tab_alignment=ft.TabAlignment.FILL,
                                        indicator_thickness=3,
                                        tabs=[
                                            ft.Tab(label=t("participant")),
                                            ft.Tab(label=t("booth_map")),
                                        ],
                                    ),
                                    ft.Container(
                                        expand=True,
                                        content=ft.TabBarView(
                                            controls=[
                                                ft.Container(
                                                    expand=True,
                                                    padding=10,
                                                    content=ft.Column(
                                                        expand=True,
                                                        spacing=10,
                                                        controls=[
                                                            ft.Text(
                                                                t("participant_info"),
                                                                size=20,
                                                                weight=ft.FontWeight.BOLD,
                                                            ),
                                                            search_field,
                                                            participant_list,
                                                        ],
                                                    ),
                                                ),
                                                ft.Container(
                                                    expand=True,
                                                    padding=10,
                                                    content=ft.Column(
                                                        expand=True,
                                                        spacing=12,
                                                        scroll=ft.ScrollMode.AUTO,
                                                        controls=[
                                                            ft.Text(
                                                                t("booth_map"),
                                                                size=20,
                                                                weight=ft.FontWeight.BOLD,
                                                            ),
                                                            ft.Text(
                                                                t("booth_map_desc"),
                                                                size=13,
                                                            ),
                                                            map_view,
                                                            ft.Text(
                                                                t("booth_list"),
                                                                size=18,
                                                                weight=ft.FontWeight.BOLD,
                                                            ),
                                                            booth_list,
                                                            ft.Text(
                                                                t("booth_update"),
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

    # ==============================
    # 홈 게스트 카드 → 뉴스 > 공개 > 게스트
    # ==============================
    def open_guest_news(e):
        change_page(index=1)

        news_tabs_control.selected_index = 1

        news_tab_changed(
            selected_index=1
        )

        page.update()

    # 하단 메뉴 연결
    navigation.on_change = change_page

    # 콘텐츠 영역
    content_area = ft.Container(
        expand=True,
        content=build_home_view(),
    )

    page.navigation_bar = navigation

    # ==============================
    # 55분마다 공식 공지 + X + Instagram 확인
    # ==============================
    async def auto_refresh_news():
        nonlocal news_initialized

        while True:
            await asyncio.sleep(3300)

            if not notifications_enabled:
                continue

            news_items = fetch_all_news() or []

            if not news_initialized:
                for item in news_items:
                    if item["url"] not in seen_news:
                        seen_news.append(item["url"])

                news_initialized = True
                save_settings()
                print("기존 소식 초기화 완료")
                continue

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

            for item in new_items:
                seen_news.append(item["url"])

            if news_content is not None:
                for item in reversed(new_items):
                    news_content.controls.insert(
                        0,
                        build_news_card(item),
                    )

            for item in new_items:
                show_windows_notification(
                    f"{t('app_title')} {get_news_source_text(item)} {t('new_update')}",
                    item["title"],
                    item["url"],
                )

            save_settings()

            if news_content is not None:
                page.update()

    page.run_task(auto_refresh_news)

    page.add(content_area)

    # ==============================
    # 베타 테스트 안내 팝업
    # ==============================
    def show_beta_dialog():
        dialog = ft.AlertDialog(
            title=ft.Text(
                t("beta_dialog_title"),
                weight=ft.FontWeight.BOLD,
            ),
            content=ft.Text(
                t("beta_dialog_message"),
                size=15,
            ),
            actions=[
                ft.TextButton(
                    t("close"),
                    on_click=lambda e: page.pop_dialog(),
                ),
            ],
        )

        page.show_dialog(dialog)

    show_beta_dialog()
    refresh_home_sns()


app = ft.run(main, export_asgi_app=True)

if __name__ == "__main__":
    ft.run(main)
