"""데이터베이스 초기화 스크립트"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import init_db, engine
from app.models import BacktestRun, BacktestTrade, BacktestEquity


def main():
    """데이터베이스 테이블 생성"""
    print("🔧 데이터베이스 테이블 생성 중...")

    try:
        init_db()
        print("✅ 데이터베이스 테이블이 생성되었습니다.")

        # 테이블 목록 확인
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\n생성된 테이블: {', '.join(tables)}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
