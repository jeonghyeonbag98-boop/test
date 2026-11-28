"""Assign each question a study topic (card id) by ordered keyword rules + manual overrides.
usage: python3 -I topics.py <app/data.json> <overrides.json|-> <out.json>
"""
import json, re, sys, collections
d = json.load(open(sys.argv[1]))
over = json.load(open(sys.argv[2])) if sys.argv[2] != '-' else {}
R = {1: [
 ('c1-copyright', r'저작권|정보 윤리|개인정보|정보 사회|정보사회'),
 ('c1-crypt', r'암호화|암호 기법|공개키|비밀키|대칭|RSA|DES|전자 서명|인증서|방화벽|Firewall|보안 기법'),
 ('c1-threat', r'바이러스|악성|웜|트로이|스니핑|스푸핑|피싱|파밍|DoS|DDoS|랜섬|백도어|키로거|해킹|크래킹|침입|위조|변조|가로채기|가로막기|보안 위협|정보 보안|보안 요건|충족 요건|부인 방지|스파이웨어'),
 ('c1-graphic', r'비트맵|벡터|그래픽|이미지|JPEG|GIF|PNG|디더링|안티앨리어싱|렌더링|모핑|모델링|인터레이싱|그림 파일'),
 ('c1-av', r'오디오|사운드|MIDI|WAV|MP3|동영상|MPEG|AVI|샘플링|스트리밍|코덱|멀티미디어|가상 현실|증강|비디오'),
 ('c1-protocol', r'프로토콜|TCP|UDP|HTTP|FTP|SMTP|POP3|IMAP|MIME|OSI|ARP|ICMP|DHCP|SNMP|Telnet'),
 ('c1-ip', r'IP 주소|IPv4|IPv6|도메인|DNS|URL|서브넷|주소 체계'),
 ('c1-netdev', r'라우터|허브|스위치|리피터|브리지|게이트웨이|네트워크 장비|모뎀|통신망|토폴로지|Topology|성형|링형|버스형|망형|LAN|WAN|MAN|VAN|클라이언트/서버|P2P|동배간|통신 장비|네트워크 운영'),
 ('c1-newtech', r'사물 인터넷|IoT|클라우드|빅데이터|빅 데이터|유비쿼터스|RFID|NFC|텔레매틱스|블록체인|메타버스|핀테크|테더링|와이파이|Wi-Fi|WiFi|블루투스|Bluetooth|와이브로|5G|LTE|엣지|그리드|USN|키오스크|웨어러블|M2M|인공지능|챗봇|정보 통신 기술|ICT|SNS|스마트|모바일|위치 기반|VoIP|IPTV|디지털 트윈|마이데이터|NFT'),
 ('c1-internet', r'인터넷|웹 브라우저|쿠키|전자우편|전자 우편|이메일|웹|HTML|XML|하이퍼|검색 엔진|인트라넷|엑스트라넷|포털'),
 ('c1-programming', r'프로그래밍|프로그램 언어|언어|컴파일러|인터프리터|어셈블러|객체 지향|JAVA|Java|C\+\+|Python|링커|로더|번역'),
 ('c1-software', r'셰어웨어|프리웨어|데모|트라이얼|알파|베타|패치|번들|애드웨어|사용권|소프트웨어|유틸리티|오픈 소스'),
 ('c1-os', r'운영체제|운영 방식|일괄 처리|실시간 처리|시분할|다중 프로그래밍|다중 처리|분산 처리|듀얼|임베디드|제어 프로그램|처리 프로그램|성능 평가|처리 능력|반환 시간|사용 가능도|신뢰도|처리 방식|정보처리 방식'),
 ('c1-classify', r'아날로그|디지털 컴퓨터|하이브리드|컴퓨터의 분류|세대별|세대|슈퍼컴퓨터|메인 프레임|미니컴퓨터|워크스테이션|마이크로컴퓨터|노트북|태블릿'),
 ('c1-data', r'비트|바이트|워드|진수|진법|보수|코드|BCD|ASCII|EBCDIC|유니코드|패리티|해밍|부동 소수점|고정 소수점|자료의 표현|자료 표현|니블|데이터 표현|데이터를 표현|정수'),
 ('c1-cpu', r'중앙처리장치|CPU|레지스터|제어장치|연산장치|누산기|가산기|보수기|명령어|마이크로프로세서|CISC|RISC|클럭|MIPS|코어|프로그램 카운터|프로세서'),
 ('c1-memory', r'메모리|기억장치|ROM|RAM|캐시|가상 기억|연관|플래시|DRAM|SRAM|버퍼|접근 속도'),
 ('c1-storage', r'하드디스크|하드 디스크|SSD|HDD|RAID|광 디스크|광디스크|블루레이|DVD|트랙|섹터|실린더|탐색 시간|보조기억|디스크'),
 ('c1-io', r'입출력|입력장치|입력 장치|출력장치|출력 장치|채널|인터럽트|DMA|버스|포트|USB|HDMI|직렬|병렬|모니터|해상도|픽셀|재생률|PPM|dpi|LCD|OLED|스캐너|터치|주변장치|그래픽 카드|사운드 카드|장치의 연결|인터페이스|썬더볼트'),
 ('c1-pcmaint', r'BIOS|바이오스|CMOS|부팅|POST|업그레이드|장치를 교체|문제 해결|펌웨어|드라이버|문제점|증상|해결 방법|관리 방법|유지 보수|PC 관리|컴퓨터 관리'),
 ('c1-winkey', r'바로 가기 키|단축키|\[Ctrl\]\s*\+|\[Alt\]\s*\+|\[Windows\]|\[⊞\]|\[Shift\]\s*\+'),
 ('c1-winprint', r'프린터|인쇄'),
 ('c1-winnet', r'네트워크 및 인터넷|ipconfig|ping|tracert|nslookup|네트워크 연결|공유|네트워크|IP|원격'),
 ('c1-winadmin', r'작업 관리자|디스크 관리|드라이브 오류|디스크 정리|조각 모음|최적화|백업|복구|레지스트리|장치 관리자|시스템 정보|성능|리소스|이벤트 뷰어|가상 데스크톱|Windows 보안|Defender|업데이트|프로그램 및 기능|시스템 구성|관리 도구'),
 ('c1-winfile', r'파일 탐색기|폴더|파일|휴지통|바로 가기 아이콘|바로 가기|즐겨찾기|라이브러리|검색|압축|숨김|확장명|클립보드'),
 ('c1-winset', r'설정|제어판|작업 표시줄|시작 메뉴|바탕 화면|개인 설정|디스플레이|접근성|계정|앱|글꼴|마우스|키보드|화면 보호기|알림|Windows|윈도우|창'),
], 2: [
 ('x2-vba', r'VBA|프로시저|\bSub\b|Range\(|Cells\(|\bDim\b|MsgBox|InputBox|Workbooks|Worksheets|ActiveCell|Do While|For Each|모듈|매크로 코드|코드'),
 ('x2-macro', r'매크로'),
 ('x2-pivot', r'피벗'),
 ('x2-whatif', r'목표값|시나리오|데이터 표|“표” 기능|해 찾기|가상 분석'),
 ('x2-subtotal', r'부분합|데이터 통합|\[통합\]|통합 기능|통합\(|개요|윤곽'),
 ('x2-filter', r'필터|정렬'),
 ('x2-chart', r'차트|추세선|오차 막대|범례|계열|스파크라인'),
 ('x2-print', r'인쇄|페이지 설정|페이지 나누기|머리글|바닥글|여백|용지|페이지 레이아웃'),
 ('x2-external', r'외부 데이터|텍스트 나누기|중복된 항목|중복 제거|빠른 채우기|가져오기|Query|파워 쿼리|웹 쿼리'),
 ('x2-protect', r'보호|암호'),
 ('x2-cond', r'조건부 서식'),
 ('x2-format', r'표시 형식|서식 코드|사용자 지정 서식|셀 서식'),
 ('x2-error', r'오류|#DIV|#N/A|#NAME|#REF|#VALUE|#NUM|#NULL|순환 참조'),
 ('x2-array', r'배열'),
 ('x2-fdb', r'\bD(SUM|AVERAGE|COUNTA?|MAX|MIN|GET|PRODUCT|STDEV|VAR)\(|\b(PMT|FV|PV|NPV|SLN|DDB|SYD|IPMT|PPMT|RATE)\('),
 ('x2-flookup', r'\b(VLOOKUP|HLOOKUP|INDEX|MATCH|CHOOSE|OFFSET|XLOOKUP|LOOKUP|ROWS?|COLUMNS?|ADDRESS|INDIRECT|TRANSPOSE)\('),
 ('x2-ftext', r'\b(LEFT|RIGHT|MID|FIND|SEARCH|REPLACE|SUBSTITUTE|TEXT|FIXED|REPT|PROPER|UPPER|LOWER|TRIM|CONCAT|CONCATENATE|LEN|VALUE|TODAY|NOW|DATE|YEAR|MONTH|DAY|WEEKDAY|EDATE|EOMONTH|WORKDAY|NETWORKDAYS|DAYS|HOUR|MINUTE|SECOND|TIME|DATEVALUE|WEEKNUM)\('),
 ('x2-fstat', r'\b(SUMIFS?|COUNTIFS?|AVERAGEIFS?|SUMPRODUCT|LARGE|SMALL|RANK(\.EQ|\.AVG)?|MEDIAN|MODE(\.SNGL)?|STDEV(\.S)?|VAR(\.S)?|FREQUENCY|COUNTA|COUNTBLANK|COUNT|AVERAGEA?|MAXA?|MINA?|PERCENTILE(\.INC)?|QUARTILE(\.INC)?|ROUND(UP|DOWN)?|INT|TRUNC|MOD|QUOTIENT|ABS|POWER|SQRT|PRODUCT|SUM|RAND(BETWEEN)?|CEILING|FLOOR|SIGN|FACT)\('),
 ('x2-flogic', r'\b(IFS?|AND|OR|NOT|IFERROR|SWITCH|ISBLANK|ISERROR|ISERR|ISTEXT|ISNUMBER|ISEVEN|ISODD|TYPE|N|CELL|XOR)\('),
 ('x2-ref', r'참조|이름 정의|이름 상자|이름 관리자|수식 입력|수식의 입력|수식 작성|수식 표시|수식 분석|연산자'),
 ('x2-input', r'데이터 입력|입력 방법|입력 작업|입력하는 방법|데이터를 입력|채우기|데이터 유효성|유효성 검사|메모|노트|하이퍼링크|윗주|자동 완성|날짜 데이터|시간 데이터|날짜와 시간|특수 문자|한자'),
 ('x2-edit', r'셀 포인터|이동|선택|찾기|바꾸기|붙여넣기|복사|시트 보호|시트 이름|시트 탭|시트 삽입|워크시트 관리|틀 고정|창 나누기|창 정렬|숨기기|통합 문서|화면|리본|옵션|저장|파일 형식|도형|SmartArt|개체|확대|축소|표 서식|엑셀|바로 가기 키|상태 표시줄|공유|편집|삭제|삽입'),
], 3: [
 ('d3-sql', r'\bSELECT\b|\bSelect\b|\bINSERT\b|\bInsert\b|\bUPDATE\b|\bUpdate\b|\bDELETE\b|\bDelete\b|CREATE|ALTER|\bDROP\b|SQL|질의문|GROUP BY|ORDER BY|JOIN|하위 쿼리|UNION|Group By|Order By|Having|HAVING'),
 ('d3-normal', r'정규화|정규형|이상 현상|이상\(Anomaly\)|함수적 종속|함수 종속'),
 ('d3-macro', r'DoCmd|매크로|이벤트|VBA|프로시저|모듈|GoTo|OpenForm|OpenReport|RunSQL|MessageBox|Recordset|Access 개체|Private Sub'),
 ('d3-func', r'DLook[Uu]p|DSum|DCount|DAvg|DMax|DMin|\bIIf\(|도메인 함수|DateAdd|DateDiff|DatePart|\bNz\(|Format\(|(?<!적 )(?<!매크로 )함수(?!적)'),
 ('d3-mask', r'입력 마스크'),
 ('d3-relation', r'관계|참조 무결성|일대다|다대다|조인 유형|조인 속성'),
 ('d3-import', r'가져오기|내보내기|연결 테이블|외부 데이터|ODBC'),
 ('d3-report', r'보고서|\[Page\]|\[Pages\]|페이지 번호|우편 엽서|누적 합계|중복 내용'),
 ('d3-control', r'컨트롤|콤보 상자|목록 상자|텍스트 상자|레이블|옵션 그룹|토글|명령 단추|바운드|언바운드|탭 순서|조건부 서식'),
 ('d3-form', r'폼'),
 ('d3-query', r'쿼리|크로스탭|매개 변수|불일치|중복 데이터|와일드 ?카드|만능 문자|\bLike\b|\bBetween\b|찾기|바꾸기|정렬|필터'),
 ('d3-table', r'테이블|필드|데이터 형식|필드 크기|유효성 검사|기본값|인덱스|형식|조회|캡션|필수|빈 문자열|일련 번호|첨부 파일|OLE|하이퍼링크|Yes/No|짧은 텍스트|긴 텍스트|데이터시트|레코드'),
 ('d3-model', r'릴레이션|튜플|속성|애트리뷰트|도메인|차수|카디널리티|기본\s?키|후보\s?키|대체\s?키|슈퍼\s?키|외래\s?키|무결성|E-R|개체|관계형|키'),
 ('d3-concept', r'데이터베이스|DBMS|스키마|DBA|관리자|DDL|DML|DCL|독립성|설계|트랜잭션|데이터 사전|파일 시스템'),
]}
def txt(bs): return re.sub(r'⟦[^⟧]*⟧', '', ' '.join(b.get('s', '') for b in bs))
def norm(q):
    st = re.sub(r'^(다음 중|다음은|아래의?|다음의?)\s*', '', txt(q['stem']))
    st = re.sub(r'\s*(에 대한|에 관한|의) 설명으로.*$|\s*(으로|로) (옳|올바|틀|적절|가장).*$', '', st)
    return re.sub(r'\W', '', st)[:28]
# an override also applies to identical copies of the question in other sets
gover = {}
for sid, qs in d['q'].items():
    for q in qs:
        k = '%s/%d' % (sid, q['n'])
        if k in over: gover[(q['s'], norm(q))] = over[k]
out, miss = {}, []
for sid, qs in d['q'].items():
    for q in qs:
        k = '%s/%d' % (sid, q['n'])
        if k in over: out[k] = over[k]; continue
        if (q['s'], norm(q)) in gover: out[k] = gover[(q['s'], norm(q))]; continue
        stem = txt(q['stem']); allt = stem + ' || ' + ' | '.join(txt(c) for c in q['ch'])
        hit = None
        for src in [stem, allt]:
            for tid, rx in R[q['s']]:
                if re.search(rx, allt if tid.startswith('x2-f') else src): hit = tid; break
            if hit: break
        if hit: out[k] = hit
        else: miss.append(k)
json.dump(out, open(sys.argv[3], 'w'), indent=0)
c = collections.Counter(out.values())
for s in (1, 2, 3):
    print(s, ' '.join('%s:%d' % (t, c[t]) for t, _ in R[s]))
print('unmatched', len(miss), miss)
