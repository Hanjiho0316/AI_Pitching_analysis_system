from app import create_app, db
from app.models.pitcher import Pitcher

# 모델에서 파싱될 소문자 라벨명 기준으로 중복을 제거한 데이터 리스트입니다.
# 형식: {"model_label": "모델출력명(소문자)", "name_en": "공식영문명", "name_ko": "한글명", "desc": "특징"}
SEED_DATA = [
    {
        "model_label": "2011clifflee.mp4", 
        "name_en": "clifflee", 
        "name_ko": "클리프 리", 
        "desc": ""
    },
    {
        "model_label": "2014Yunsungwhan.mp4",
        "name_en": "yunsunghwan",
        "name_ko": "윤성환",
        "desc": ""
    },
    {
        "model_label": "2015Clayton.mp4",
        "name_en": "claytonkershaw",
        "name_ko": "클레이튼 커쇼",
        "desc": ""
    },
    {
        "model_label": "2015Josangwoo.mp4",
        "name_en": "chosangwoo",
        "name_ko": "조상우",
        "desc": ""
    },
    {
        "model_label": "2015Youheekwan.mp4",
        "name_en": "yooheekwan",
        "name_ko": "유희관",
        "desc": ""
    },
    {
        "model_label": "2015chawoochan",
        "name_en": "chawoochan",
        "name_ko": "차우찬",
        "desc": ""
    },
    {
        "model_label": "2015chrisoxspring.mp4",
        "name_en": "chrisoxspring",
        "name_ko": "크리스 옥스프링",
        "desc": ""
    },
    {
        "model_label": "2015mitchtalbot.mp4",
        "name_en": "mitchtalbot",
        "name_ko": "미치 탈보트",
        "desc": ""
    },
    {
        "model_label": "2015songchangsik.mp4",
        "name_en": "songchangsik",
        "name_ko": "송창식",
        "desc": ""
    },
    {
        "model_label": "2015sonseunglock",
        "name_en": "sonseunglak",
        "name_ko": "손승락",
        "desc": ""
    },
    {
        "model_label": "2015yoongilhyeon.mp4",
        "name_en": "yunkilhyoun",
        "name_ko": "윤길현",
        "desc": ""
    },
    {
        "model_label": "2016Dustinnipurt.mp4",
        "name_en": "dustinnippert",
        "name_ko": "더스틴 니퍼트",
        "desc": ""
    },
    {
        "model_label": "2016Limchangmin.mp4",
        "name_en": "limchangmin",
        "name_ko": "임창민",
        "desc": ""
    },
    {
        "model_label": "2016MichaelBowden.mp4",
        "name_en": "michaelbowden",
        "name_ko": "마이클 보우덴",
        "desc": ""
    },
    {
        "model_label": "2016kimjinsung.mp4",
        "name_en": "kimjinsung",
        "name_ko": "김진성",
        "desc": ""
    },
    {
        "model_label": "2016kwonhyeok.mp4",
        "name_en": "kwonhyuk",
        "name_ko": "권혁",
        "desc": ""
    },
    {
        "model_label": "2016ryujegook.mp4",
        "name_en": "ryujaekuk",
        "name_ko": "류제국",
        "desc": ""
    },
    {
        "model_label": "2017Brooks.mp4",
        "name_en": "brooksraley",
        "name_ko": "브룩스 레일리",
        "desc": ""
    },
    {
        "model_label": "2017CoryKluber.mp4",
        "name_en": "coreykluber",
        "name_ko": "코리 클루버",
        "desc": ""
    },
    {
        "model_label": "2017Merrillkelly.mp4",
        "name_en": "merrillkelly",
        "name_ko": "메릴 켈리",
        "desc": ""
    },
    {
        "model_label": "2017Ryan.mp4",
        "name_en": "ryanfeierabend",
        "name_ko": "라이언 피어밴드",
        "desc": ""
    },
    {
        "model_label": "2017Yanghyunjong.mp4",
        "name_en": "yanghyeonjong",
        "name_ko": "양현종",
        "desc": ""
    },
    {
        "model_label": "2017parkjinhyeong.mp4",
        "name_en": "parkjinhyung",
        "name_ko": "박진형",
        "desc": ""
    },
    {
        "model_label": "2017yooheekwan.mp4",
        "name_en": "yooheekwan",
        "name_ko": "유희관",
        "desc": ""
    },
    {
        "model_label": "2018DavidHail.mp4",
        "name_en": "davidhale",
        "name_ko": "데이비드 헤일",
        "desc": ""
    },
    {
        "model_label": "2018Henrysosa.mp4",
        "name_en": "henrysosa",
        "name_ko": "헨리 소사",
        "desc": ""
    },
    {
        "model_label": "2018Kimtaehoon.mp4",
        "name_en": "kimtaehoon",
        "name_ko": "김태훈",
        "desc": ""
    },
    {
        "model_label": "2018LeeYongChan.mp4",
        "name_en": "leeyongchan",
        "name_ko": "이용찬",
        "desc": ""
    },
    {
        "model_label": "2018jacobdegrom.mp4",
        "name_en": "jacobdegrom",
        "name_ko": "제이콥 디그롬",
        "desc": ""
    },
    {
        "model_label": "2018kimkwanghyeon.mp4",
        "name_en": "kimwanghyun",
        "name_ko": "김광현",
        "desc": ""
    },
    {
        "model_label": "2019angelsanchez.mp4",
        "name_en": "angelsanchez",
        "name_ko": "앙헬 산체스",
        "desc": ""
    },
    {
        "model_label": "2019breekum",
        "name_en": "jakebrigham",
        "name_ko": "제이크 브리검",
        "desc": ""
    },
    {
        "model_label": "2019leeseungho",
        "name_en": "leeseungho",
        "name_ko": "이승호",
        "desc": ""
    },
    {
        "model_label": "2019seojinyong.mp4",
        "name_en": "seojinyong",
        "name_ko": "서진용",
        "desc": ""
    },
    {
        "model_label": "2020Baejaesung.mp4",
        "name_en": "baejeseong",
        "name_ko": "배제성",
        "desc": ""
    },
    {
        "model_label": "2020Guchangmo.mp4",
        "name_en": "koochangmo",
        "name_ko": "구창모",
        "desc": ""
    },
    {
        "model_label": "2020KimTaeHoon.mp4",
        "name_en": "kimtaehoon",
        "name_ko": "김태훈",
        "desc": ""
    },
    {
        "model_label": "2020Sohyungjun.mp4",
        "name_en": "sohyeongjun",
        "name_ko": "소형준",
        "desc": ""
    },
    {
        "model_label": "2020TrevorBauer.mp4",
        "name_en": "trevorbauer",
        "name_ko": "트레버 바우어",
        "desc": ""
    },
    {
        "model_label": "2020imchankyu.mp4",
        "name_en": "limchankyu",
        "name_ko": "임찬규",
        "desc": ""
    },
    {
        "model_label": "2020moonseungwon",
        "name_en": "moonseungwon",
        "name_ko": "문승원",
        "desc": ""
    },
    {
        "model_label": "2020yanghyunjong",
        "name_en": "yanghyeonjong",
        "name_ko": "양현종",
        "desc": ""
    },
    {
        "model_label": "2021Baekjunghyun.mp4",
        "name_en": "baekjunghyun",
        "name_ko": "백정현",
        "desc": ""
    },
    {
        "model_label": "2021Goyoungpo.mp4",
        "name_en": "koyoungpyo",
        "name_ko": "고영표",
        "desc": ""
    },
    {
        "model_label": "2021Kimjaeyoon.mp4",
        "name_en": "kimjaeyun",
        "name_ko": "김재윤",
        "desc": ""
    },
    {
        "model_label": "2021kimminwoo",
        "name_en": "kimminwoo",
        "name_ko": "김민우",
        "desc": ""
    },
    {
        "model_label": "2021wesparsons.mp4",
        "name_en": "wesparsons",
        "name_ko": "웨스 파슨스",
        "desc": ""
    },
    {
        "model_label": "2021wontaein.mp4",
        "name_en": "wontaein",
        "name_ko": "원태인",
        "desc": ""
    },
    {
        "model_label": "2022Anwoojin.mp4",
        "name_en": "anwoojin",
        "name_ko": "안우진",
        "desc": ""
    },
    {
        "model_label": "2022DarvishYu",
        "name_en": "yudarvish",
        "name_ko": "다르빗슈 유",
        "desc": ""
    },
    {
        "model_label": "2022Guseungmin.mp4",
        "name_en": "kooseungmin",
        "name_ko": "구승민",
        "desc": ""
    },
    {
        "model_label": "2022KimWonJung.mp4",
        "name_en": "kimwonjung",
        "name_ko": "김원중",
        "desc": ""
    },
    {
        "model_label": "2022KooChangMo.mp4",
        "name_en": "koochangmo",
        "name_ko": "구창모",
        "desc": ""
    },
    {
        "model_label": "2022Wilmerfont.mp4",
        "name_en": "wilmerfont",
        "name_ko": "윌머 폰트",
        "desc": ""
    },
    {
        "model_label": "2022baejaesung",
        "name_en": "baejeseong",
        "name_ko": "배제성",
        "desc": ""
    },
    {
        "model_label": "2022eomsangbaek",
        "name_en": "umsangback",
        "name_ko": "엄상백",
        "desc": ""
    },
    {
        "model_label": "2022kimkwanghyun",
        "name_en": "kimkwanghyun",
        "name_ko": "김광현",
        "desc": ""
    },
    {
        "model_label": "2022kimminsu.mp4",
        "name_en": "kimminsu",
        "name_ko": "김민수",
        "desc": ""
    },
    {
        "model_label": "2022kimsihoon",
        "name_en": "kimsihoon",
        "name_ko": "김시훈",
        "desc": ""
    },
    {
        "model_label": "2022kimyoonsik.mp4",
        "name_en": "kimyunsik",
        "name_ko": "김윤식",
        "desc": ""
    },
    {
        "model_label": "2022sohyeongjun.mp4",
        "name_en": "sohyeongjun",
        "name_ko": "소형준",
        "desc": ""
    },
    {
        "model_label": "2023Ericpaddy.mp4",
        "name_en": "erickfedde",
        "name_ko": "에릭 페디",
        "desc": ""
    },
    {
        "model_label": "2023Kawkbin.mp4",
        "name_en": "gwakbeen",
        "name_ko": "곽빈",
        "desc": ""
    },
    {
        "model_label": "2023Moondongju.mp4",
        "name_en": "moondongju",
        "name_ko": "문동주",
        "desc": ""
    },
    {
        "model_label": "2023Nagyunan.mp4",
        "name_en": "nagyunan",
        "name_ko": "나균안",
        "desc": ""
    },
    {
        "model_label": "2023WesBenjamin.mp4",
        "name_en": "wesbenjamin",
        "name_ko": "웨스 벤자민",
        "desc": ""
    },
    {
        "model_label": "2023elias",
        "name_en": "roeniselias",
        "name_ko": "로에니스 엘리아스",
        "desc": ""
    },
    {
        "model_label": "2023gohyojun",
        "name_en": "kohyojun",
        "name_ko": "고효준",
        "desc": ""
    },
    {
        "model_label": "2023kimjinsung",
        "name_en": "kimjinsung",
        "name_ko": "김진성",
        "desc": ""
    },
    {
        "model_label": "2025AroldisChapman",
        "name_en": "aroldischapman",
        "name_ko": "아롤디스 채프먼",
        "desc": ""
    },
    {
        "model_label": "2025GregorySoto.mp4",
        "name_en": "gregorysoto",
        "name_ko": "그레고리 소토",
        "desc": ""
    },
    {
        "model_label": "2025PaulSkenes",
        "name_en": "paulskenes",
        "name_ko": "폴 스킨스",
        "desc": ""
    },
    {
        "model_label": "2025Ponce.mp4",
        "name_en": "codyponce",
        "name_ko": "코디 폰세",
        "desc": ""
    },
    {
        "model_label": "2025SasakiLoki",
        "name_en": "rokisasaki",
        "name_ko": "사사키 로키",
        "desc": ""
    },
    {
        "model_label": "2025SengaKodai.mp4",
        "name_en": "kodaisenga",
        "name_ko": "센가 코다이",
        "desc": ""
    },
    {
        "model_label": "2025SpencerSchwellenbach",
        "name_en": "spencerschwellenbach",
        "name_ko": "스펜서 슈웰렌바크",
        "desc": ""
    },
    {
        "model_label": "2025YamamotoYoshinobu.mp4",
        "name_en": "yoshinobuyamamoto",
        "name_ko": "야마모토 요시노부",
        "desc": ""
    },
    {
        "model_label": "2025ohtani",
        "name_en": "shoheiohtani",
        "name_ko": "오타니 쇼헤이",
        "desc": ""
    }
]

app = create_app()

with app.app_context():
    print("데이터베이스 초기화 작업을 시작합니다...")

    db.create_all()
    
    # 데이터 삽입
    count = 0
    for data in SEED_DATA:
        # 이미 존재하는 라벨인지 확인하여 중복 삽입을 방지합니다.
        exists = Pitcher.query.filter_by(model_label=data["model_label"]).first()
        if not exists:
            pitcher = Pitcher(
                model_label=data["model_label"],
                name_en=data["name_en"],
                name_ko=data["name_ko"],
                description=data["desc"]
            )
            db.session.add(pitcher)
            count += 1
            
    db.session.commit()
    print(f"총 {count}명의 투수 정보가 성공적으로 데이터베이스에 추가되었습니다!")