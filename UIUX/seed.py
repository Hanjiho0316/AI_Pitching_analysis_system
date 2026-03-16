"""
어플리케이션 초기 구동 시 필요한 기본 투수 데이터(Seed Data)를 
데이터베이스에 적재하는 스크립트입니다.
Flask 앱 컨텍스트 내에서 실행되며, 기존에 데이터가 있는지 확인하여 
중복 적재를 방지합니다.
"""
from app import create_app, db
from app.models.analysis import Analysis
from app.models.pitcher import Pitcher
from app.models.hitter import Hitter # 타자 모델 임포트 추가
from app.models.user import User

# 모델에서 파싱될 소문자 라벨명 기준으로 중복을 제거한 데이터 리스트입니다.
# 형식: {"model_label": "모델출력명(소문자)", "name_en": "공식영문명", "name_ko": "한글명", "desc": "특징"}
PITCHER_SEED_DATA = [
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
        "desc": "100마일 이상의 강속구와 날카로운 스플리터를 앞세워 메이저리그를 지배하는 투타겸업의 신화"
    }
]

HITTER_SEED_DATA = [
    {
        "model_label": "choijung",
        "name_en": "choijeong",
        "name_ko": "최정",
        "desc": "KBO 리그 역대 최다 홈런 기록을 보유한 완벽한 스윙 메커니즘의 우완 거포"
    },
    {
        "model_label": "KimHaseong",
        "name_en": "kimhaseong",
        "name_ko": "김하성",
        "desc": "뛰어난 배트 컨트롤과 매서운 펀치력을 바탕으로 메이저리그 투수들을 공략하는 만능 타자"
    },
    {
        "model_label": "nasungbum",
        "name_en": "nasungbum",
        "name_ko": "나성범",
        "desc": "부드러운 폼에서 나오는 폭발적인 파워로 거침없이 담장을 넘기는 리그 정상급 좌타 거포"
    },
    {
        "model_label": "WillSmith",
        "name_en": "willsmith",
        "name_ko": "윌 스미스",
        "desc": "정교한 선구안과 우수한 장타력을 겸비하여 팀의 중심 타선을 책임지는 공격형 포수"
    },
    {
        "model_label": "mike_trout",
        "name_en": "miketrout",
        "name_ko": "마이크 트라웃",
        "desc": "폭발적인 파워와 정교함을 동시에 갖춘 현대 야구 최고의 완성형 타자"
    },
    {
        "model_label": "ohtani",
        "name_en": "shoheiohtani",
        "name_ko": "오타니 쇼헤이",
        "desc": "압도적인 비거리와 빠른 스윙 스피드로 홈런왕을 차지한 현대 야구의 아이콘"
    },
    {
        "model_label": "AustinDean",
        "name_en": "austindean",
        "name_ko": "오스틴 딘",
        "desc": "특유의 파워풀한 스윙과 훌륭한 컨택 능력으로 팀의 공격을 이끄는 듬직한 외국인 타자"
    },
    {
        "model_label": "JulioRodriguez",
        "name_en": "juliorodriguez",
        "name_ko": "훌리오 로드리게스",
        "desc": "경이로운 배트 스피드와 장타력을 겸비하여 차세대 메이저리그를 이끌어갈 슈퍼스타"
    },
    {
        "model_label": "BobbyWittJr",
        "name_en": "bobbywittjr",
        "name_ko": "바비 위트 주니어",
        "desc": "정교한 타격 기술과 폭발적인 장타력으로 그라운드를 지배하는 특급 유격수"
    },
    {
        "model_label": "YasielPuig",
        "name_en": "yasielpuig",
        "name_ko": "야시엘 푸이그",
        "desc": "타고난 근력과 역동적인 스윙으로 투수를 압도하는 야생마 같은 타자"
    },
    {
        "model_label": "ChaeEunseong",
        "name_en": "chaeeunseong",
        "name_ko": "채은성",
        "desc": "정확한 타격 기술과 뛰어난 클러치 능력을 바탕으로 타점을 쓸어담는 우완 거포"
    },
    {
        "model_label": "HwangSungBin",
        "name_en": "hwangseongbin",
        "name_ko": "황성빈",
        "desc": "빠른 발을 살린 기습 번트와 끈질긴 컨택 능력으로 내야를 뒤흔드는 교타자"
    },
    {
        "model_label": "parkhaemin",
        "name_en": "parkhaemin",
        "name_ko": "박해민",
        "desc": "정교한 배트 컨트롤과 탁월한 기동력을 자랑하는 리그 최고 수준의 리드오프"
    },
    {
        "model_label": "SeiyaSuzuki",
        "name_en": "seiyasuzuki",
        "name_ko": "스즈키 세이야",
        "desc": "뛰어난 선구안과 일발 장타력을 겸비하여 메이저리그 투수들에게도 위협적인 우타자"
    },
    {
        "model_label": "ChoiHyungWoo",
        "name_en": "choihyoungwoo",
        "name_ko": "최형우",
        "desc": "KBO 리그 역대 최고의 클러치 히터이자 부드러운 스윙의 좌타 거포"
    },
    {
        "model_label": "ManyMachado",
        "name_en": "mannymachado",
        "name_ko": "매니 마차도",
        "desc": "완벽한 타격 메커니즘과 강한 손목 힘을 이용해 큼지막한 타구를 만들어내는 거포"
    },
    {
        "model_label": "TreaTurner",
        "name_en": "treaturner",
        "name_ko": "트레아 터너",
        "desc": "간결한 스윙에서 나오는 장타력과 압도적인 스피드를 자랑하는 정상급 내야수"
    },
    {
        "model_label": "LeeJungHoo",
        "name_en": "leejunghoo",
        "name_ko": "이정후",
        "desc": "어떤 공이든 쳐낼 수 있는 약점이 없는 완벽한 컨택 능력의 소유자"
    },
    {
        "model_label": "BrandonLowe",
        "name_en": "brandonlowe",
        "name_ko": "브랜든 로우",
        "desc": "체구는 작지만 빠르고 간결한 스윙으로 묵직한 타구를 날리는 좌타 거포"
    },
    {
        "model_label": "freddie_freeman",
        "name_en": "freddiefreeman",
        "name_ko": "프레디 프리먼",
        "desc": "메이저리그에서 가장 아름다운 스윙을 바탕으로 꾸준히 장타를 생산하는 좌타자"
    },
    {
        "model_label": "parkchanho",
        "name_en": "parkchanho",
        "name_ko": "박찬호",
        "desc": "정교한 컨택 능력과 빠른 발을 활용해 공격의 활로를 뚫어주는 내야수"
    },
    {
        "model_label": "hongchangki",
        "name_en": "hongchangki",
        "name_ko": "홍창기",
        "desc": "리그 최고 수준의 선구안과 끈질긴 승부로 출루의 정석을 보여주는 교타자"
    },
    {
        "model_label": "kimhyesung",
        "name_en": "kimhyeseong",
        "name_ko": "김혜성",
        "desc": "정확한 배트 컨트롤과 폭발적인 주력으로 안타를 만들어내는 안타 제조기"
    },
    {
        "model_label": "KimDoyeong",
        "name_en": "kimdoyeong",
        "name_ko": "김도영",
        "desc": "폭발적인 배트 스피드와 파워를 겸비하여 리그의 차세대 슈퍼스타로 자리매김한 거포"
    },
    {
        "model_label": "moonbokyung",
        "name_en": "moonbogyeong",
        "name_ko": "문보경",
        "desc": "안정적인 타격 밸런스와 날카로운 스윙으로 팀의 중심 타선을 이끄는 좌타자"
    },
    {
        "model_label": "giancarlo_stanton",
        "name_en": "giancarlostanton",
        "name_ko": "지안카를로 스탠튼",
        "desc": "압도적인 근력과 경이로운 타구 속도로 초대형 홈런을 쏘아 올리는 괴력의 거포"
    },
    {
        "model_label": "VladimirGuerreroJr",
        "name_en": "vladimirguerrerojr",
        "name_ko": "블라디미르 게레로 주니어",
        "desc": "아버지의 재능을 물려받아 경이로운 파워와 정교함을 보여주는 우타 거포"
    },
    {
        "model_label": "yangeuiji",
        "name_en": "yangeuiji",
        "name_ko": "양의지",
        "desc": "부드럽고 간결한 스윙으로 언제든 담장을 넘길 수 있는 역대 최고의 공격형 포수"
    },
    {
        "model_label": "koojawook",
        "name_en": "kooJawook",
        "name_ko": "구자욱",
        "desc": "정교한 타격과 폭발적인 장타력을 두루 갖춘 라이온즈의 상징적인 좌타자"
    },
    {
        "model_label": "HwangJaegyun",
        "name_en": "hwangjaegyun",
        "name_ko": "황재균",
        "desc": "강한 손목 힘을 바탕으로 승부처마다 짜릿한 장타를 터뜨리는 베테랑 내야수"
    },
    {
        "model_label": "jeonjunwoo",
        "name_en": "jeonjunwoo",
        "name_ko": "전준우",
        "desc": "특유의 밀어치기 기술과 꾸준한 타격감을 자랑하는 자이언츠의 프랜차이즈 스타"
    },
    {
        "model_label": "mookie_betts",
        "name_en": "mookiebetts",
        "name_ko": "무키 베츠",
        "desc": "체구를 뛰어넘는 폭발적인 파워와 정교한 컨택을 자랑하는 메이저리그의 아이콘"
    },
    {
        "model_label": "GuillermoHeredia",
        "name_en": "guillermoheredia",
        "name_ko": "기예르모 에레디아",
        "desc": "부드러운 타격 리듬과 정확한 컨택 능력으로 팀 공격의 혈을 뚫어주는 타자"
    },
    {
        "model_label": "parksunghan",
        "name_en": "parkseonghan",
        "name_ko": "박성한",
        "desc": "정교한 선구안과 결대로 밀어치는 타격 기술이 일품인 좌타 내야수"
    },
    {
        "model_label": "nojinhyeok",
        "name_en": "nohjinhyuk",
        "name_ko": "노진혁",
        "desc": "결정적인 순간에 장타를 쳐내는 클러치 능력이 돋보이는 거포형 유격수"
    },
    {
        "model_label": "JungSooBin",
        "name_en": "jungsoobin",
        "name_ko": "정수빈",
        "desc": "끈질긴 커트와 정확한 컨택 능력으로 그라운드를 휘젓는 리그 정상급 리드오프"
    },
    {
        "model_label": "GabrielMoreno",
        "name_en": "gabrielmoreno",
        "name_ko": "가브리엘 모레노",
        "desc": "부드러운 스윙과 정교한 타격 기술을 갖춘 차세대 메이저리그 공격형 포수"
    },
    {
        "model_label": "PeteCrow-Armstrong",
        "name_en": "petecrowarmstrong",
        "name_ko": "피트 크로 암스트롱",
        "desc": "빠른 배트 스피드와 폭발적인 주력을 바탕으로 타선에 활력을 불어넣는 유망주"
    },
    {
        "model_label": "ohjihwan",
        "name_en": "ohjihwan",
        "name_ko": "오지환",
        "desc": "강력한 일발 장타력과 끈질긴 승부 근성으로 팀을 이끄는 베테랑 유격수"
    },
    {
        "model_label": "chooshinsoo",
        "name_en": "chooshinsoo",
        "name_ko": "추신수",
        "desc": "뛰어난 선구안과 묵직한 장타력으로 메이저리그를 호령했던 출루 머신"
    },
    {
        "model_label": "austin_riley",
        "name_en": "austinriley",
        "name_ko": "오스틴 라일리",
        "desc": "강력한 파워와 부드러운 스윙을 앞세워 큼지막한 홈런을 만들어내는 우타 거포"
    },
    {
        "model_label": "corey_seager",
        "name_en": "coreyseager",
        "name_ko": "코리 시거",
        "desc": "메이저리그 최고 수준의 정교함과 파워를 겸비한 좌타 유격수"
    },
    {
        "model_label": "yordan_alvarez",
        "name_en": "yordanalvarez",
        "name_ko": "요르단 알바레즈",
        "desc": "가볍게 치는 듯한 스윙으로도 경이로운 비거리를 만들어내는 압도적인 좌타 거포"
    },
    {
        "model_label": "EricTames",
        "name_en": "erictames",
        "name_ko": "에릭 테임즈",
        "desc": "압도적인 파워와 정교한 타격으로 KBO 리그를 폭격했던 전설적인 외국인 타자"
    },
    {
        "model_label": "fernando_tatis_jr",
        "name_en": "fernandotatisjr",
        "name_ko": "페르난도 타티스 주니어",
        "desc": "역동적인 폼과 엄청난 배트 스피드로 투수를 압도하는 천재 타자"
    },
    {
        "model_label": "juan_soto",
        "name_en": "juansoto",
        "name_ko": "후안 소토",
        "desc": "투수의 공을 완벽하게 읽어내는 선구안과 타석에서의 여유가 돋보이는 천재 타자"
    },
    {
        "model_label": "sonahseop",
        "name_en": "sonahseop",
        "name_ko": "손아섭",
        "desc": "매서운 스윙과 정교한 배트 컨트롤로 안타를 양산하는 리그 최고의 교타자"
    },
    {
        "model_label": "bryce_harper",
        "name_en": "bryceharper",
        "name_ko": "브라이스 하퍼",
        "desc": "폭발적인 스윙과 압도적인 스타성으로 타석을 지배하는 메이저리그의 간판타자"
    },
    {
        "model_label": "AhnHyunmin",
        "name_en": "ahnhyunmin",
        "name_ko": "안현민",
        "desc": "강력한 손목 힘과 매서운 스윙으로 장타를 생산하는 차세대 유망주 거포"
    },
    {
        "model_label": "julio_rodríguez",
        "name_en": "juliorodriguez",
        "name_ko": "훌리오 로드리게스",
        "desc": "경이로운 배트 스피드와 장타력을 겸비하여 차세대 메이저리그를 이끌어갈 슈퍼스타"
    },
    {
        "model_label": "aaronjudge",
        "name_en": "aaronjudge",
        "name_ko": "에런 저지",
        "desc": "경이로운 체격에서 나오는 압도적인 파워로 메이저리그 홈런 기록을 써 내려가는 거포"
    },
    {
        "model_label": "ronald_acuña_jr",
        "name_en": "ronaldacunajr",
        "name_ko": "로날드 아쿠냐 주니어",
        "desc": "호쾌한 타격과 압도적인 파워로 그라운드를 지배하는 만능형 슈퍼스타"
    },
    {
        "model_label": "kangbaekho",
        "name_en": "kangbaekho",
        "name_ko": "강백호",
        "desc": "데뷔 초부터 완성형 타격 메커니즘을 뽐내며 리그를 호령하는 천재 좌타자"
    },
    {
        "model_label": "KimJooChan",
        "name_en": "kimjoochan",
        "name_ko": "김주찬",
        "desc": "매서운 스윙과 정교한 컨택으로 수많은 라인드라이브 타구를 만들어낸 베테랑 타자"
    },
    {
        "model_label": "pete_alonso",
        "name_en": "petealonso",
        "name_ko": "피트 알론소",
        "desc": "특유의 파워풀한 어퍼스윙으로 큼지막한 홈런을 생산하는 메츠의 북극곰 거포"
    },
    {
        "model_label": "AlejandroKirk",
        "name_en": "alejandrokirk",
        "name_ko": "알레한드로 커크",
        "desc": "콤팩트한 스윙과 정교한 타격 기술을 자랑하는 메이저리그의 공격형 포수"
    },
    {
        "model_label": "RohSihwan",
        "name_en": "rohsihwan",
        "name_ko": "노시환",
        "desc": "구장을 훌쩍 넘기는 묵직한 파워와 부드러운 스윙을 갖춘 차세대 중심 거포"
    },
    {
        "model_label": "NicoHoerner",
        "name_en": "nicohoerner",
        "name_ko": "니코 호너",
        "desc": "삼진을 잘 당하지 않는 정교한 컨택과 교과서적인 타격 폼을 자랑하는 내야수"
    },
    {
        "model_label": "LeeSeungYeop",
        "name_en": "leeseungyuop",
        "name_ko": "이승엽",
        "desc": "부드러운 스윙과 폭발적인 장타력으로 대한민국 야구 역사에 한 획을 그은 국민타자"
    }
]

app = create_app()

with app.app_context():
    """
    앱 컨텍스트를 활성화하여 데이터베이스 테이블을 생성하고 
    투수 및 타자 시드 데이터를 삽입합니다.
    """
    print("데이터베이스 초기화 작업을 시작합니다...")

    db.create_all()
    
    # 투수 데이터 적재
    pitcher_count = 0
    for data in PITCHER_SEED_DATA:
        exists = Pitcher.query.filter_by(model_label=data["model_label"]).first()

        if not exists:
            pitcher = Pitcher(
                model_label=data["model_label"],
                name_en=data["name_en"],
                name_ko=data["name_ko"],
                description=data["desc"]
            )
            db.session.add(pitcher)
            pitcher_count += 1
            
    # 타자 데이터 적재
    hitter_count = 0
    for data in HITTER_SEED_DATA:
        exists = Hitter.query.filter_by(model_label=data["model_label"]).first()

        if not exists:
            hitter = Hitter(
                model_label=data["model_label"],
                name_en=data["name_en"],
                name_ko=data["name_ko"],
                description=data["desc"]
            )
            db.session.add(hitter)
            hitter_count += 1
        
    # 변경사항을 데이터베이스에 최종 반영합니다.
    db.session.commit()
    print(f"총 {pitcher_count}명의 투수 정보가 성공적으로 데이터베이스에 추가되었습니다!")
    print(f"총 {hitter_count}명의 타자 정보가 성공적으로 데이터베이스에 추가되었습니다!")