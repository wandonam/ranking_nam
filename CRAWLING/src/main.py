import sys
from channels import naver, coupang, oliveyoung, kakao, daiso

JOBS = {
    "naver": naver.run,
    "coupang": coupang.run,
    "oliveyoung": oliveyoung.run,
    "kakao": kakao.run,
    "daiso": daiso.run,
}

def run_one(name):
    try:
        JOBS[name]()
    except Exception as e:
        print(f"[오류] {name}: {e}")

def main():
    print("크롤링 시작")

    if len(sys.argv) == 1 or sys.argv[1] == "--all":
        for name in JOBS:
            run_one(name)
    else:
        for target in sys.argv[1:]:
            target = target.lower()
            if target in JOBS:
                run_one(target)
            else:
                print(f"[오류] 지원하지 않는 채널: {target}")

    print("크롤링 종료")

if __name__ == "__main__":
    main()