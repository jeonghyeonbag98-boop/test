# 컴활 1급 필기 CBT

모바일에서 컴퓨터활용능력 1급 필기 기출·유형 문제를 풀고, 즉시 채점·풀이 확인·오답 횟수 기록을 하는 한 페이지 앱입니다.

- `index.html` — 앱 화면. 같은 폴더의 `data.json`과 `img/`를 불러옵니다.
- `tools/extract.py` — PDF에서 문제·보기·그림·정답을 추출합니다.
- `tools/match.py` — 기출 문제와 유형별 자료의 해설을 짝지어 줍니다.
- `tools/build.py` — 추출 결과와 해설(`expl/*.json`)을 합쳐 `data.json`을 만듭니다.

문제 원문, 그림, 해설은 시나공 자료(개인 학습용, 재배포 금지)를 바탕으로 하므로 이 공개 저장소에는 포함하지 않습니다.

## 다시 만들기

```sh
pip install pymupdf pillow
python3 tools/extract.py pdf/y2025_1.pdf y2025_1 exam out     # 기출: exam, 유형별: topic
python3 tools/match.py                                         # out/ 안에서 실행
python3 tools/build.py out expl .                              # data.json + img/ 생성
```

풀이 기록은 claude.ai 아티팩트의 사용자별 저장소(`data/users/<id>/state`)에 저장되고, 없으면 브라우저 localStorage에 저장됩니다.
