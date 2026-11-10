import flet as ft

# AGF 연도 자동화
# ==============================

CURRENT_YEAR = 2026
AGF_TITLE = f"AGF {CURRENT_YEAR} 정보"

# 부스 화면용 참가사 데이터
participants = []

# 공개 탭용 AGF 2026 참가사 목록
PUBLIC_PARTICIPANT_ANNOUNCEMENTS = [
    {
        "title": "1차 공개",
        "url": "https://x.com/AGF_Korea/status/2111985688489119820",
        "names": [
            "넥슨",
            "스마일게이트",
            "구글 플레이",
            "주식회사 홀로시브",
            "YOSTAR",
            "주식회사 스콘",
        ],
    },
    {
        "title": "2차 공개",
        "url": "https://x.com/AGF_Korea/status/2112348077592125884",
        "names": [
            "브라운더스트2",
            "고양이와 스프",
            "케이티스튜디오지니",
            "NIJISANJI",
            "주식회사 팀테트라포드",
        ],
    },
    {
        "title": "3차 공개",
        "url": "https://x.com/AGF_Korea/status/2112710469253271899",
        "names": [
            "세가/아틀러스",
            "Crunchyroll",
            "에스엠지홀딩스",
            "Lenovo",
            "크레플",
            "한림사",
            "스튜디오 그린기린",
            "XEROmotion",
        ],
    },
    {
        "title": "4차 공개",
        "url": "https://x.com/AGF_Korea/status/2113072850311782679",
        "names": [
            "뱅드림! 아워 노트",
            "GNFTOYZ",
            "럭앤픽",
            "요시요시 스튜디오",
            "디엠피 북스토아",
            "잇츠하비",
            "T toy studio",
        ],
    },
    {
        "title": "5차 공개",
        "url": "https://x.com/AGF_Korea/status/2113435239292846384",
        "names": [
            "젠잇",
            "하이라이트 픽",
            "코멧소프트",
            "카하문방구",
            "하나미즈온천아카데미 커플쳐부수기",
            "스태커배틀",
        ],
    },
    {
        "title": "6차 공개",
        "url": "https://x.com/AGF_Korea/status/2114522398980710649",
        "names": [
            "승리의 여신: 니케",
            "트릭컬 리바이브",
            "포카이브 스테이션",
            "이스타에그",
            "샤카샤카",
            "크리에이터버스",
            "스튜디오 세뇨",
        ],
    },
    {
        "title": "7차 공개",
        "url": "https://x.com/AGF_Korea/status/2114884789710852600",
        "names": [
            "베이비챗",
            "ASL / 화모선",
            "BLOKEES",
            "주식회사 키쿠",
            "가우리피규어",
            "프레젠스월드",
        ],
    },
    {
        "title": "8차 공개",
        "url": "https://x.com/AGF_Korea/status/2115247179975799016",
        "names": [
            "위메이드커넥트",
            "(주)디앤씨미디어",
            "peropero",
            "VO6 TCG",
            "VLooM",
            "미스틱뮤즈",
            "MW:MEU",
        ],
    },
    {
        "title": "9차 공개",
        "url": "https://x.com/AGF_Korea/status/2115609562392736136",
        "names": [
            "페이트/그랜드 오더",
            "아크시스템웍스 아시아",
            "(주)소미미디어",
            "밸로프",
            "하비프러스",
            "플로토이",
            "animate KOREA",
            "대원미디어 그룹",
        ],
    },
    {
        "title": "10차 공개",
        "url": "https://x.com/AGF_Korea/status/2115971951953055901",
        "names": [
            "SBS아카데미 게임학원",
            "한국영상대학교 만화웹툰콘텐츠과",
            "배재대학교 게임애니메이션전공",
            "콘텐츠 인재들의 부트캠프, GCC사관학교",
            "민화",
            "국경없는의사회",
        ],
    },
    {
        "title": "11차 공개",
        "url": "https://x.com/AGF_Korea/status/2117059120629195093",
        "names": [
            "hololive Dreams",
            "viviON",
            "Hakuhodo DY Music & Pictures Inc.",
            "Bushiroad",
            "Minboo LTD",
            "탭웨이브",
        ],
    },
    {
        "title": "12차 공개",
        "url": "https://x.com/AGF_Korea/status/2117421502215905377",
        "names": [
            "스마일게이트 희망스튜디오",
            "애니프릭스",
            "주식회사 에어캡",
            "KADOKAWA",
            "Japan Pavilion",
            "노벨피아",
            "주식회사 와이앤케이미디어",
            "위프",
        ],
    },
]

# 공개된 참가사를 부스 화면에 표시합니다.
# 공식 부스 번호가 공개되지 않은 경우 임의로 지정하지 않습니다.
participants = [
    {"name": name, "booth": "미공개"}
    for name in dict.fromkeys(
        name
        for announcement in PUBLIC_PARTICIPANT_ANNOUNCEMENTS
        for name in announcement["names"]
    )
]

# 공식 공개된 RED 스테이지 일정
PUBLIC_RED_STAGE = {
    "12월 5일(토)": [
        {
            "time": "11:45~12:30",
            "title": "주홍색 가면",
            "guest": "키무라 타이히 · 야마모토 유우키 · 남도형 · 이여름",
        },
        {
            "time": "13:00~13:45",
            "title": "페이트/그랜드 오더 스테이지",
            "guest": "타카하시 리에 · 아카바네 켄지",
        },
        {
            "time": "14:15~15:00",
            "title": "추후 공개",
            "guest": "출연진 추후 공개",
        },
        {
            "time": "15:30~16:15",
            "title": "반딧불이의 혼례",
            "guest": "Lynn · 우치야마 코우키",
        },
        {
            "time": "16:45~17:30",
            "title": "Re: 제로부터 시작하는 이세계 생활 스페셜 스테이지",
            "guest": "코바야시 유스케 · 타카하시 리에",
        },
    ],
    "12월 6일(일)": [
        {
            "time": "10:30~11:15",
            "title": "NIJISANJI_AGF2026",
            "guest": "3SKM · 키타미 유우세이 · 카이세이 · 사카키 네스",
        },
        {
            "time": "11:45~12:30",
            "title": "극장판 마법소녀 마도카☆마기카 〈발푸르기스의 회천〉",
            "guest": "사이토 치와 · 카토 에미리",
        },
        {
            "time": "13:00~13:45",
            "title": "GACHIAKUTA",
            "guest": "이치카와 아오이 · 코니시 카츠유키",
        },
        {
            "time": "14:15~15:00",
            "title": "최애의 아이 스페셜 스테이지",
            "guest": "이고마 유리에 · 한 메구미",
        },
        {
            "time": "15:30~16:15",
            "title": "고깔모자의 아틀리에 스페셜 스테이지",
            "guest": "모토무라 레나 · 하나에 나츠키",
        },
        {
            "time": "17:00~17:45",
            "title": "DJ Kazu CLOSING PARTY",
            "guest": "DJ Kazu",
        },
    ],
}



TICKET_URL = "https://ticket.melon.com/csoon/detail.htm?csoonId=12858"
RED_STAGE_SOURCE_URL = "https://x.com/AGF_Korea/status/2115322678319976772"
OFFICIAL_X_URL = "https://x.com/AGF_Korea"


def make_panel(content, bgcolor="#FFFFFF"):
    return ft.Container(
        margin=12,
        padding=16,
        border_radius=14,
        bgcolor=bgcolor,
        content=content,
    )


def main(page: ft.Page):
    page.title = "AGF 2026"
    page.padding = 0
    page.bgcolor = "#F6F7F9"
    page.appbar = ft.AppBar(
        title=ft.Text("AGF 2026", weight=ft.FontWeight.BOLD),
        center_title=True,
        bgcolor="#FFFFFF",
        elevation=1,
    )

    disclaimer = ft.Container(
        margin=ft.Margin(left=14, right=14, top=12, bottom=8),
        padding=12,
        border_radius=10,
        bgcolor="#FFF2D9",
        content=ft.Column(
            spacing=3,
            tight=True,
            controls=[
                ft.Text(
                    "비공식 팬메이드 사이트",
                    size=15,
                    weight=ft.FontWeight.BOLD,
                    color="#8A4B08",
                ),
                ft.Text(
                    "AGF 공식 웹사이트·앱이 아니며, AGF Korea와 공식 제휴 또는 운영 관계가 없습니다.",
                    size=12,
                    color="#76521E",
                ),
            ],
        ),
    )

    ticket_view = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            make_panel(
                ft.Column(
                    spacing=10,
                    controls=[
                        ft.Text("🎟️ 티켓 예매", size=22, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "AGF 2026",
                            size=17,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text("2026년 12월 4일(금) – 12월 6일(일)"),
                        ft.Text("킨텍스 제1전시장"),
                        ft.Divider(),
                        ft.Text(
                            "예매 일정, 티켓 가격 및 잔여 좌석은 멜론티켓 공식 페이지에서 확인하세요.",
                            color="#555555",
                        ),
                        ft.Button(
                            "멜론티켓에서 예매하기",
                            icon=ft.Icons.OPEN_IN_NEW,
                            url=TICKET_URL,
                        ),
                    ],
                ),
                bgcolor="#E8F5EC",
            ),
        ],
    )

    participant_controls = []
    for announcement in PUBLIC_PARTICIPANT_ANNOUNCEMENTS:
        participant_controls.append(
            make_panel(
                ft.Column(
                    spacing=9,
                    controls=[
                        ft.Text(
                            announcement["title"],
                            size=16,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            "\n".join(f"• {name}" for name in announcement["names"]),
                            size=14,
                        ),
                        ft.TextButton(
                            "공식 발표 원문 보기",
                            icon=ft.Icons.OPEN_IN_NEW,
                            url=announcement["url"],
                        ),
                    ],
                )
            )
        )

    participants_view = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Container(
                padding=ft.Padding(left=14, right=14, top=12, bottom=0),
                content=ft.Text(
                    "공식 채널에서 공개된 참가사 목록입니다.",
                    size=13,
                    color="#666666",
                ),
            ),
            *participant_controls,
        ],
    )

    stage_date_names = ["12월 4일(금)", "12월 5일(토)", "12월 6일(일)"]

    def build_red_stage_view():
        controls = []
        for date_name in stage_date_names:
            rows = PUBLIC_RED_STAGE.get(date_name, [])
            date_controls = [
                ft.Text(date_name, size=17, weight=ft.FontWeight.BOLD)
            ]

            if rows:
                for item in rows:
                    date_controls.append(
                        ft.Container(
                            padding=12,
                            border_radius=10,
                            bgcolor="#F5F5F5",
                            content=ft.Column(
                                spacing=4,
                                controls=[
                                    ft.Text(
                                        item["time"],
                                        size=13,
                                        weight=ft.FontWeight.BOLD,
                                        color="#A33B3B",
                                    ),
                                    ft.Text(
                                        item["title"],
                                        size=15,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        item["guest"],
                                        size=13,
                                        color="#555555",
                                    ),
                                ],
                            ),
                        )
                    )
            else:
                date_controls.append(
                    ft.Text(
                        "공식 일정 미공개",
                        size=13,
                        color="#777777",
                    )
                )

            controls.append(
                make_panel(ft.Column(spacing=9, controls=date_controls))
            )

        controls.append(
            ft.Container(
                padding=ft.Padding(left=14, right=14, top=0, bottom=12),
                content=ft.TextButton(
                    "RED 스테이지 공식 발표 원문",
                    icon=ft.Icons.OPEN_IN_NEW,
                    url=RED_STAGE_SOURCE_URL,
                ),
            )
        )

        return ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=controls,
        )

    blue_stage_view = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            make_panel(
                ft.Column(
                    spacing=10,
                    controls=[
                        ft.Text(
                            "BLUE STAGE",
                            size=22,
                            weight=ft.FontWeight.BOLD,
                            color="#315F9B",
                        ),
                        ft.Text(
                            "BLUE 스테이지 세부 일정은 공식 발표 전입니다.",
                            size=15,
                        ),
                        ft.Text(
                            "공식 일정이 공개되면 확인 가능한 내용만 업데이트합니다.",
                            size=13,
                            color="#666666",
                        ),
                        ft.TextButton(
                            "AGF Korea 공식 X 확인",
                            icon=ft.Icons.OPEN_IN_NEW,
                            url=OFFICIAL_X_URL,
                        ),
                    ],
                ),
                bgcolor="#EAF1FA",
            )
        ],
    )

    main_tabs = ft.Tabs(
        length=4,
        selected_index=0,
        expand=True,
        content=ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ft.TabBar(
                    scrollable=True,
                    tab_alignment=ft.TabAlignment.FILL,
                    indicator_thickness=3,
                    tabs=[
                        ft.Tab(label="티켓"),
                        ft.Tab(label="참가사"),
                        ft.Tab(label="RED STAGE"),
                        ft.Tab(label="BLUE STAGE"),
                    ],
                ),
                ft.Container(
                    expand=True,
                    content=ft.TabBarView(
                        controls=[
                            ticket_view,
                            participants_view,
                            build_red_stage_view(),
                            blue_stage_view,
                        ],
                    ),
                ),
            ],
        ),
    )

    page.add(
        ft.Column(
            expand=True,
            spacing=0,
            controls=[
                disclaimer,
                main_tabs,
            ],
        )
    )


if __name__ == "__main__":
    ft.run(main)
else:
    app = ft.run(main, export_asgi_app=True)
