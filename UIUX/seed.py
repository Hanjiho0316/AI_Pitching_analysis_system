"""
어플리케이션 초기 구동 시 필요한 기본 투수 데이터(Seed Data)를 
데이터베이스에 적재하는 스크립트입니다.
Flask 앱 컨텍스트 내에서 실행되며, 기존에 데이터가 있는지 확인하여 
중복 적재를 방지합니다.
"""
from app import create_app, db
from app.models.analysis import Analysis
from app.models.pitcher import Pitcher
from app.models.user import User

# 모델에서 파싱될 소문자 라벨명 기준으로 중복을 제거한 데이터 리스트입니다.
# 형식: {"model_label": "모델출력명(소문자)", "name_en": "공식영문명", "name_ko": "한글명", "desc": "특징"}
SEED_DATA = [
    {
        "model_label": "2011clifflee.mp4", 
        "name_en": "clifflee", 
        "name_ko": "클리프 리", 
        "desc": "자로 잰 듯한 제구력으로 메이저리그를 평정했던 좌완 마스터"
    },
    {
        "model_label": "2014Yunsungwhan.mp4",
        "name_en": "yunsunghwan",
        "name_ko": "윤성환",
        "desc": "황태자라 불릴 만큼 완벽한 제구력과 낙차 큰 커브의 소유자"
    },
    {
        "model_label": "2015Clayton.mp4",
        "name_en": "claytonkershaw",
        "name_ko": "클레이튼 커쇼",
        "desc": "한 시대를 풍미한 최고의 좌완 투수이자 폭포수 커브의 상징"
    },
    {
        "model_label": "2015Josangwoo.mp4",
        "name_en": "chosangwoo",
        "name_ko": "조상우",
        "desc": "150km/h 중반대의 묵직한 속구로 타자를 윽박지르는 괴력의 소유자"
    },
    {
        "model_label": "2015Youheekwan.mp4",
        "name_en": "yooheekwan",
        "name_ko": "유희관",
        "desc": "느린 공으로도 타자를 제압하는 제구의 마술사"
    },
    {
        "model_label": "2015chawoochan",
        "name_en": "chawoochan",
        "name_ko": "차우찬",
        "desc": "강력한 구위와 탈삼진 능력을 겸비한 '강철 어깨' 좌완 투수"
    },
    {
        "model_label": "2015chrisoxspring.mp4",
        "name_en": "chrisoxspring",
        "name_ko": "크리스 옥스프링",
        "desc": "너클볼을 섞어 던지며 리그에서 활약한 베테랑 투수"
    },
    {
        "model_label": "2015mitchtalbot.mp4",
        "name_en": "mitchtalbot",
        "name_ko": "미치 탈보트",
        "desc": "뛰어난 변화구 구사 능력과 영리한 경기 운영이 돋보이는 투수"
    },
    {
        "model_label": "2015songchangsik.mp4",
        "name_en": "songchangsik",
        "name_ko": "송창식",
        "desc": "팀을 위해 언제든 마운드에 올랐던 '투혼'의 상징이자 폭포수 커브의 달인"
    },
    {
        "model_label": "2015sonseunglock",
        "name_en": "sonseunglak",
        "name_ko": "손승락",
        "desc": "긁히는 날은 막을수 없었던 마무리 투수"
    },
    {
        "model_label": "2015yoongilhyeon.mp4",
        "name_en": "yunkilhyoun",
        "name_ko": "윤길현",
        "desc": "전성기 시절 리그 최고 수준의 슬라이더를 뿌렸던 우완 필승조"
    },
    {
        "model_label": "2016Andrewmiller.mp4",
        "name_en": "andrewmiller",
        "name_ko": "앤드류 밀러",
        "desc": "압도적인 신장의 좌완 파이어볼러"
    },
    {
        "model_label": "2016Dustinnipurt.mp4",
        "name_en": "dustinnippert",
        "name_ko": "더스틴 니퍼트",
        "desc": "KBO 역대 최고의 외국인 투수 중 하나, 압도적인 타점의 니느님"
    },
    {
        "model_label": "2016Limchangmin.mp4",
        "name_en": "limchangmin",
        "name_ko": "임창민",
        "desc": "회전수 높은 속구와 영리한 수싸움으로 타자를 압도하는 우완 투수"
    },
    {
        "model_label": "2016MichaelBowden.mp4",
        "name_en": "michaelbowden",
        "name_ko": "마이클 보우덴",
        "desc": "노히트 노런을 기록할 만큼 강력한 구위와 탈삼진 능력을 갖춘 투수"
    },
    {
        "model_label": "2016kimjinsung.mp4",
        "name_en": "kimjinsung",
        "name_ko": "김진성",
        "desc": "독특한 릴리스 포인트에서 떨어지는 포크볼이 강력한 베테랑 투수"
    },
    {
        "model_label": "2016kwonhyeok.mp4",
        "name_en": "kwonhyuk",
        "name_ko": "권혁",
        "desc": "거침없는 투구와 묵직한 속구로 팬들의 심장을 뛰게 했던 불꽃 남자"
    },
    {
        "model_label": "2016ryujegook.mp4",
        "name_en": "ryujaekuk",
        "name_ko": "류제국",
        "desc": "제구력과 공의 무브먼트에서 비롯된 구위가 강력한 우완 투수"
    },
    {
        "model_label": "2017Brooks.mp4",
        "name_en": "brooksraley",
        "name_ko": "브룩스 레일리",
        "desc": "좌타자에게 공포감을 심어주는 날카로운 슬라이더를 가진 좌완"
    },
    {
        "model_label": "2017CoryKluber.mp4",
        "name_en": "coreykluber",
        "name_ko": "코리 클루버",
        "desc": "클루봇이라 불릴 만큼 정교한 제구와 무브먼트의 달인"
    },
    {
        "model_label": "2017Merrillkelly.mp4",
        "name_en": "merrillkelly",
        "name_ko": "메릴 켈리",
        "desc": "KBO를 거쳐 MLB에서도 정상급 선발로 도약한 역수출의 신화"
    },
    {
        "model_label": "2017Ryan.mp4",
        "name_en": "ryanfeierabend",
        "name_ko": "라이언 피어밴드",
        "desc": "KBO에 너클볼 열풍을 일으켰던 마구의 소유자."
    },
    {
        "model_label": "2017Yanghyunjong.mp4",
        "name_en": "yanghyeonjong",
        "name_ko": "양현종",
        "desc": "타이거즈의 상징이자 꾸준함의 대명사, KBO 역사를 새로 쓰는 대투수"
    },
    {
        "model_label": "2017parkjinhyeong.mp4",
        "name_en": "parkjinhyung",
        "name_ko": "박진형",
        "desc": "낙폭 큰 포크볼을 앞세워 타자의 헛스윙을 이끌어내는 불펜의 핵심"
    },
    {
        "model_label": "2017yooheekwan.mp4",
        "name_en": "yooheekwan",
        "name_ko": "유희관",
        "desc": "느린 공으로도 타자를 제압하는 제구의 마술사"
    },
    {
        "model_label": "2018DavidHail.mp4",
        "name_en": "davidhale",
        "name_ko": "데이비드 헤일",
        "desc": "안정적인 제구와 싱커를 바탕으로 땅볼을 유도하는 우완 투수"
    },
    {
        "model_label": "2018Henrysosa.mp4",
        "name_en": "henrysosa",
        "name_ko": "헨리 소사",
        "desc": "KBO 리그에서 오랫동안 활약하며 강속구 투수의 면모를 보여준 외인"
    },
    {
        "model_label": "2018Kimtaehoon.mp4",
        "name_en": "kimtaehoon",
        "name_ko": "김태훈",
        "desc": "정교한 제구와 변칙적인 구질로 승부하는 좌완 투수"
    },
    {
        "model_label": "2018LeeYongChan.mp4",
        "name_en": "leeyongchan",
        "name_ko": "이용찬",
        "desc": "안정적인 제구와 포크볼을 앞세워 선발과 마무리에서 모두 성공한 투수"
    },
    {
        "model_label": "2018jacobdegrom.mp4",
        "name_en": "jacobdegrom",
        "name_ko": "제이콥 디그롬",
        "desc": "현대 야구 투수의 정점, 100마일의 속구와 95마일의 슬라이더를 던지는 괴물"
    },
    {
        "model_label": "2018kimkwanghyeon.mp4",
        "name_en": "kimwanghyun",
        "name_ko": "김광현",
        "desc": "KBO를 대표하는 좌완 에이스이자 전매특허인 강력한 슬라이더의 소유자"
    },
    {
        "model_label": "2019angelsanchez.mp4",
        "name_en": "angelsanchez",
        "name_ko": "앙헬 산체스",
        "desc": "다양한 변화구, 준수한 컨트롤을 가진 우완 파이어볼러"
    },
    {
        "model_label": "2019breekum",
        "name_en": "jakebrigham",
        "name_ko": "제이크 브리검",
        "desc": "안정적인 제구와 싱커로 긴 이닝을 책임졌던 히어로즈의 장수 외인"
    },
    {
        "model_label": "2019leeseungho",
        "name_en": "leeseungho",
        "name_ko": "이승호",
        "desc": "배짱 있는 투구와 정교한 변화구로 승부하는 좌완 투수"
    },
    {
        "model_label": "2019seojinyong.mp4",
        "name_en": "seojinyong",
        "name_ko": "서진용",
        "desc": "리그 최상급의 수직 무브먼트를 자랑하는 포크볼로 뒷문을 잠그는 투수"
    },
    {
        "model_label": "2020Baejaesung.mp4",
        "name_en": "baejeseong",
        "name_ko": "배제성",
        "desc": "큰 키를 활용한 타점 높은 투구가 인상적인 kt wiz의 우완 선발"
    },
    {
        "model_label": "2020Guchangmo.mp4",
        "name_en": "koochangmo",
        "name_ko": "구창모",
        "desc": "건강하기만 하면 리그를 지배하는 'NC의 좌완 에이스'"
    },
    {
        "model_label": "2020KimTaeHoon.mp4",
        "name_en": "kimtaehoon",
        "name_ko": "김태훈",
        "desc": "정교한 제구와 변칙적인 구질로 승부하는 좌완 투수"
    },
    {
        "model_label": "2020Sohyungjun.mp4",
        "name_en": "sohyeongjun",
        "name_ko": "소형준",
        "desc": "어린 나이에도 완벽한 제구와 경기 운영 능력을 갖춘 빅게임 피처"
    },
    {
        "model_label": "2020TrevorBauer.mp4",
        "name_en": "trevorbauer",
        "name_ko": "트레버 바우어",
        "desc": "데이터 분석을 기반으로 한 다양한 구질과 압도적인 탈삼진 능력"
    },
    {
        "model_label": "2020imchankyu.mp4",
        "name_en": "limchankyu",
        "name_ko": "임찬규",
        "desc": "노련한 완급 조절과 커브를 통해 타자의 타이밍을 뺏는 LG의 에이스"
    },
    {
        "model_label": "2020moonseungwon",
        "name_en": "moonseungwon",
        "name_ko": "문승원",
        "desc": "부드러운 폼에서 나오는 강력한 속구와 슬라이더가 강점인 우완 정통파"
    },
    {
        "model_label": "2020yanghyunjong",
        "name_en": "yanghyeonjong",
        "name_ko": "양현종",
        "desc": "타이거즈의 상징이자 꾸준함의 대명사, KBO 역사를 새로 쓰는 대투수"
    },
    {
        "model_label": "2021Baekjunghyun.mp4",
        "name_en": "baekjunghyun",
        "name_ko": "백정현",
        "desc": "노련한 경기 운영과 백쇼라는 별명에 걸맞은 명품 슬라이더"
    },
    {
        "model_label": "2021Goyoungpo.mp4",
        "name_en": "koyoungpyo",
        "name_ko": "고영표",
        "desc": "고영표의 체인지업은 알고도 못 친다는 말을 증명하는 KBO 최고의 잠수함 투수"
    },
    {
        "model_label": "2021Kimjaeyoon.mp4",
        "name_en": "kimjaeyun",
        "name_ko": "김재윤",
        "desc": "묵직한 돌직구 하나로 타자를 압도하는 리그 정상급 클로저"
    },
    {
        "model_label": "2021kimminwoo",
        "name_en": "kimminwoo",
        "name_ko": "김민우",
        "desc": "높은 타점에서 내리꽂는 위력적인 포크볼이 일품인 한화의 우완 선발"
    },
    {
        "model_label": "2021wesparsons.mp4",
        "name_en": "wesparsons",
        "name_ko": "웨스 파슨스",
        "desc": "강력한 구위와 무브먼트가 좋은 변형 패스트볼을 구사하는 투수    "
    },
    {
        "model_label": "2021wontaein.mp4",
        "name_en": "wontaein",
        "name_ko": "원태인",
        "desc": "뛰어난 체인지업과 안정적인 경기 운영을 자랑하는 푸른 피의 에이스"
    },
    {
        "model_label": "2022Anwoojin.mp4",
        "name_en": "anwoojin",
        "name_ko": "안우진",
        "desc": "KBO 역대 최고의 구위와 압도적인 탈삼진 능력을 갖춘 우완 선발"
    },
    {
        "model_label": "2022DarvishYu",
        "name_en": "yudarvish",
        "name_ko": "다르빗슈 유",
        "desc": "수많은 구종을 자유자재로 구사하는 현대 야구의 피칭 마스터"
    },
    {
        "model_label": "2022Guseungmin.mp4",
        "name_en": "kooseungmin",
        "name_ko": "구승민",
        "desc": "롯데 자이언츠의 뒷문을 책임지는 강력한 포크볼러"
    },
    {
        "model_label": "2022KimWonJung.mp4",
        "name_en": "kimwonjung",
        "name_ko": "김원중",
        "desc": "긴 머리만큼이나 강렬한 구위와 포효를 보여주는 롯데의 마무리 투수"
    },
    {
        "model_label": "2022KooChangMo.mp4",
        "name_en": "koochangmo",
        "name_ko": "구창모",
        "desc": "건강하기만 하면 리그를 지배하는 NC의 좌완 에이스"
    },
    {
        "model_label": "2022Wilmerfont.mp4",
        "name_en": "wilmerfont",
        "name_ko": "윌머 폰트",
        "desc": "KBO 역사상 가장 압도적인 속구 구위를 보여주었던 우완 파이어볼러"
    },
    {
        "model_label": "2022baejaesung",
        "name_en": "baejeseong",
        "name_ko": "배제성",
        "desc": "큰 키를 활용한 타점 높은 투구가 인상적인 kt wiz의 우완 선발"
    },
    {
        "model_label": "2022eomsangbaek",
        "name_en": "umsangback",
        "name_ko": "엄상백",
        "desc": "사이드암 투수 중 보기 드문 빠른 공과 체인지업을 구사하는 선발 자원"
    },
    {
        "model_label": "2022kimkwanghyun",
        "name_en": "kimkwanghyun",
        "name_ko": "김광현",
        "desc": "KBO를 대표하는 좌완 에이스이자 전매특허인 강력한 슬라이더의 소유자"
    },
    {
        "model_label": "2022kimminsu.mp4",
        "name_en": "kimminsu",
        "name_ko": "김민수",
        "desc": "다양한 보직을 소화하며 팀의 승리를 지키는 만능 우완 투수"
    },
    {
        "model_label": "2022kimsihoon",
        "name_en": "kimsihoon",
        "name_ko": "김시훈",
        "desc": "NC 다이노스의 차세대 주역으로 꼽히는 날카로운 구위의 우완"
    },
    {
        "model_label": "2022kimyoonsik.mp4",
        "name_en": "kimyunsik",
        "name_ko": "김윤식",
        "desc": "부드러운 투구 폼에서 나오는 제구력이 장점인 LG 트윈스의 좌완 선발"
    },
    {
        "model_label": "2022sohyeongjun.mp4",
        "name_en": "sohyeongjun",
        "name_ko": "소형준",
        "desc": "완벽한 제구와 경기 운영 능력을 갖춘 빅게임 피처"
    },
    {
        "model_label": "2023Ericpaddy.mp4",
        "name_en": "erickfedde",
        "name_ko": "에릭 페디",
        "desc": "2023년 KBO를 지배한 스위퍼의 장인이자 20승 투수"
    },
    {
        "model_label": "2023Kawkbin.mp4",
        "name_en": "gwakbeen",
        "name_ko": "곽빈",
        "desc": "다양한 변화구를 구사하는 우완 정통파 강속구 투수"
    },
    {
        "model_label": "2023Moondongju.mp4",
        "name_en": "moondongju",
        "name_ko": "문동주",
        "desc": "대한민국 야구 역사상 최고 속도인 160.1km/h를 기록한 차세대 에이스"
    },
    {
        "model_label": "2023Nagyunan.mp4",
        "name_en": "nagyunan",
        "name_ko": "나균안",
        "desc": "포수에서 투수로 전향해 리그 정상급 선발로 거듭난 승리의 아이콘"
    },
    {
        "model_label": "2023WesBenjamin.mp4",
        "name_en": "wesbenjamin",
        "name_ko": "웨스 벤자민",
        "desc": "높은 타점에서 나오는 날카로운 각도의 공을 던지는 좌완 에이스"
    },
    {
        "model_label": "2023elias",
        "name_en": "roeniselias",
        "name_ko": "로에니스 엘리아스",
        "desc": "묵직한 속구와 노련한 완급 조절을 보여주는 좌완 파이어볼러"
    },
    {
        "model_label": "2023gohyojun",
        "name_en": "kohyojun",
        "name_ko": "고효준",
        "desc": "폭발적인 구위와 역동적인 투구 폼을 가진 베테랑 좌완 파이어볼러"
    },
    {
        "model_label": "2023kimjinsung",
        "name_en": "kimjinsung",
        "name_ko": "김진성",
        "desc": "독특한 릴리스 포인트에서 떨어지는 포크볼이 강력한 베테랑 투수"
    },
    {
        "model_label": "2025AroldisChapman",
        "name_en": "aroldischapman",
        "name_ko": "아롤디스 채프먼",
        "desc": "야구 역사상 가장 빠른 공을 던진 광속구의 대명사"
    },
    {
        "model_label": "2025GregorySoto.mp4",
        "name_en": "gregorysoto",
        "name_ko": "그레고리 소토",
        "desc": "좌완으로서 100마일을 넘나드는 광속구를 뿌리는 파이어볼러"
    },
    {
        "model_label": "2025PaulSkenes",
        "name_en": "paulskenes",
        "name_ko": "폴 스킨스",
        "desc": "대학 시절부터 완성형으로 평가받은 100마일 광속구의 소유자"
    },
    {
        "model_label": "2025Ponce.mp4",
        "name_en": "codyponce",
        "name_ko": "코디 폰세",
        "desc": "큰 체격을 활용한 위력적인 속구가 장점인 우완 투수"
    },
    {
        "model_label": "2025SasakiLoki",
        "name_en": "rokisasaki",
        "name_ko": "사사키 로키",
        "desc": "레이와 시대의 괴물, 160km/h 중반대의 속구와 포크볼을 던지는 천재"
    },
    {
        "model_label": "2025SengaKodai.mp4",
        "name_en": "kodaisenga",
        "name_ko": "센가 코다이",
        "desc": "유령처럼 사라지는 고스트 포크로 메이저리그를 평정한 투수"
    },
    {
        "model_label": "2025SpencerSchwellenbach",
        "name_en": "spencerschwellenbach",
        "name_ko": "스펜서 슈웰렌바크",
        "desc": "탄탄한 기본기와 완성도 높은 변화구를 갖춘 차세대 우완"
    },
    {
        "model_label": "2025YamamotoYoshinobu.mp4",
        "name_en": "yoshinobuyamamoto",
        "name_ko": "야마모토 요시노부",
        "desc": "일본 야구를 평정하고 메이저리그로 진출한 완성형 우완 에이스"
    },
    {
        "model_label": "2025ohtani",
        "name_en": "shoheiohtani",
        "name_ko": "오타니 쇼헤이",
        "desc": "투타겸업 이도류의 신화"
    }
]

app = create_app()

with app.app_context():
    """
    앱 컨텍스트를 활성화하여 데이터베이스 테이블을 생성하고 시드 데이터를 삽입합니다.
    """
    print("데이터베이스 초기화 작업을 시작합니다...")

    db.create_all()
    
    count = 0
    for data in SEED_DATA:
        # 데이터베이스에 동일한 model_label을 가진 투수가 이미 존재하는지 검사합니다.
        exists = Pitcher.query.filter_by(model_label=data["model_label"]).first()

        # 존재하지 않을 경우에만 새로운 투수 객체를 생성하여 세션에 추가합니다.
        if not exists:
            pitcher = Pitcher(
                model_label=data["model_label"],
                name_en=data["name_en"],
                name_ko=data["name_ko"],
                description=data["desc"]
            )
            db.session.add(pitcher)
            count += 1
        
    # 변경사항을 데이터베이스에 최종 반영합니다.
    db.session.commit()
    print(f"총 {count}명의 투수 정보가 성공적으로 데이터베이스에 추가되었습니다!")