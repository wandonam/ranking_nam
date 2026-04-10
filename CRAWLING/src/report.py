from datetime import datetime
from pathlib import Path
import pandas as pd
import openpyxl


# ================= 설정 =================
BASE_DB = Path(r'..\00_Database')
OUTPUT_PATH = Path(r'..\01_Result')

PLATFORMS = {
    'naver':      {'dir': '01_naver',      'diff_cols': ['price', 'review', 'rank', 'star']},
    'coupang':    {'dir': '02_coupang',    'diff_cols': ['price', 'review', 'rank', 'star']},
    'oliveyoung': {'dir': '03_oliveyoung', 'diff_cols': ['price', 'rank']},
    'kakao':      {'dir': '04_kakao',      'diff_cols': ['price', 'rank', 'like']},
    'daiso':      {'dir': '05_daiso',      'diff_cols': ['price', 'review', 'rank', 'star']},
}

HOT_THRESHOLD = 10
DOWN_THRESHOLD = -10


# ================= 함수 =================
def load_latest_two(base_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """디렉토리에서 최신 2개 CSV 파일을 읽어 반환."""
    csv_files = sorted(base_path.glob('*.csv'), key=lambda x: x.stem, reverse=True)
    if len(csv_files) < 2:
        raise FileNotFoundError(f"CSV 파일이 2개 이상 필요합니다: {base_path}")
    return pd.read_csv(csv_files[0]), pd.read_csv(csv_files[1])


def calc_diff(latest_df: pd.DataFrame, previous_df: pd.DataFrame, diff_cols: list) -> pd.DataFrame:
    """이전 데이터와 비교해 diff 컬럼을 추가."""
    df = latest_df.copy()
    prev = previous_df.set_index('code')

    for col in diff_cols:
        df[f'prev_{col}'] = df['code'].map(prev[col])

    # rank_diff는 순위가 올라갈수록 양수 (prev - current)
    for col in diff_cols:
        if col == 'rank':
            df['rank_diff'] = df['prev_rank'] - df['rank']
        else:
            df[f'{col}_diff'] = df[f'{col}'] - df[f'prev_{col}']

    df.drop(columns=[c for c in df.columns if c.startswith('prev_')], inplace=True)
    return df


def split_by_rank(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """TOP 10 / 급등 / 급락 데이터프레임으로 분리."""
    top10 = df[df['rank'].between(1, 10)]
    hot   = df[df['rank_diff'] >= HOT_THRESHOLD]
    down  = df[df['rank_diff'] <= DOWN_THRESHOLD]
    return top10, hot, down


def process_platform(name: str, config: dict) -> dict:
    """플랫폼 하나를 처리해 {name_10, name_hot, name_down} 딕셔너리 반환."""
    base_path = BASE_DB / config['dir'] / '01_healthyfood'
    latest_df, previous_df = load_latest_two(base_path)
    df = calc_diff(latest_df, previous_df, config['diff_cols'])
    top10, hot, down = split_by_rank(df)
    return {
        f'{name}_10':   top10,
        f'{name}_hot':  hot,
        f'{name}_down': down,
    }


# ================= 메인 =================
def main():
    results = {}
    for name, config in PLATFORMS.items():
        results.update(process_platform(name, config))

    today = datetime.now().strftime('%Y%m%d')
    output_file = OUTPUT_PATH / f'{today}_ranking.xlsx'
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        for sheet_name, df in results.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"저장 완료: {output_file}")


if __name__ == '__main__':
    main()
