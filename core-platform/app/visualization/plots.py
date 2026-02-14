"""백테스팅 결과 시각화"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Dict, Any, Optional
from pathlib import Path


class BacktestVisualizer:
    """백테스팅 결과 시각화"""

    def __init__(self, results: Dict[str, Any], output_dir: Optional[str] = None):
        """
        Args:
            results: BacktestEngine.run()의 결과
            output_dir: 그래프 저장 디렉토리 (None이면 화면에만 표시)
        """
        self.results = results
        self.output_dir = Path(output_dir) if output_dir else None

        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)

        # DataFrames 생성
        self.equity_df = pd.DataFrame(results["equity_curve"])
        self.trades_df = pd.DataFrame(results["trades"]) if results["trades"] else pd.DataFrame()

        # 한글 폰트 설정 (macOS)
        plt.rcParams['font.family'] = 'AppleGothic'
        plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

    def plot_equity_curve(self, save: bool = True, show: bool = False):
        """자산 곡선 그래프"""
        fig, ax = plt.subplots(figsize=(14, 6))

        ax.plot(
            self.equity_df["timestamp"],
            self.equity_df["equity"],
            linewidth=2,
            color="#2E86AB",
            label="자산 총액",
        )

        # 초기 자본 기준선
        ax.axhline(
            y=self.results["initial_capital"],
            color="gray",
            linestyle="--",
            alpha=0.5,
            label="초기 자본",
        )

        # 수익률 텍스트
        final_return = self.results["total_return"]
        color = "green" if final_return > 0 else "red"
        ax.text(
            0.02,
            0.98,
            f"총 수익률: {final_return:.2f}%",
            transform=ax.transAxes,
            fontsize=14,
            fontweight="bold",
            color=color,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        )

        ax.set_title(
            f"자산 곡선 - {self.results['strategy_name']} ({self.results['symbol']})",
            fontsize=16,
            fontweight="bold",
        )
        ax.set_xlabel("날짜", fontsize=12)
        ax.set_ylabel("자산 (USDT)", fontsize=12)
        ax.legend(loc="upper left", fontsize=10)
        ax.grid(True, alpha=0.3)

        # X축 날짜 포맷
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        fig.autofmt_xdate()

        plt.tight_layout()

        if save and self.output_dir:
            filepath = self.output_dir / "equity_curve.png"
            plt.savefig(filepath, dpi=300, bbox_inches="tight")
            print(f"✅ 저장: {filepath}")

        if show:
            plt.show()
        else:
            plt.close()

    def plot_drawdown(self, save: bool = True, show: bool = False):
        """낙폭(Drawdown) 그래프"""
        # Peak와 Drawdown 계산
        equity_df = self.equity_df.copy()
        equity_df["peak"] = equity_df["equity"].cummax()
        equity_df["drawdown"] = (
            (equity_df["equity"] - equity_df["peak"]) / equity_df["peak"]
        ) * 100

        fig, ax = plt.subplots(figsize=(14, 6))

        # Drawdown 영역 채우기
        ax.fill_between(
            equity_df["timestamp"],
            0,
            equity_df["drawdown"],
            color="#E63946",
            alpha=0.6,
            label="Drawdown",
        )

        # MDD 표시
        mdd = equity_df["drawdown"].min()
        mdd_date = equity_df.loc[equity_df["drawdown"].idxmin(), "timestamp"]

        ax.axhline(y=mdd, color="red", linestyle="--", linewidth=2, alpha=0.8)
        ax.text(
            0.02,
            0.02,
            f"최대 낙폭 (MDD): {mdd:.2f}%",
            transform=ax.transAxes,
            fontsize=14,
            fontweight="bold",
            color="red",
            verticalalignment="bottom",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        )

        ax.set_title(
            f"낙폭 (Drawdown) - {self.results['strategy_name']}",
            fontsize=16,
            fontweight="bold",
        )
        ax.set_xlabel("날짜", fontsize=12)
        ax.set_ylabel("낙폭 (%)", fontsize=12)
        ax.legend(loc="lower left", fontsize=10)
        ax.grid(True, alpha=0.3)

        # X축 날짜 포맷
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        fig.autofmt_xdate()

        plt.tight_layout()

        if save and self.output_dir:
            filepath = self.output_dir / "drawdown.png"
            plt.savefig(filepath, dpi=300, bbox_inches="tight")
            print(f"✅ 저장: {filepath}")

        if show:
            plt.show()
        else:
            plt.close()

    def plot_trades_distribution(self, save: bool = True, show: bool = False):
        """거래 손익 분포 그래프"""
        if self.trades_df.empty:
            print("⚠️  거래 데이터가 없어 분포 그래프를 생성할 수 없습니다.")
            return

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # 1. 손익률 히스토그램
        pnl_pcts = self.trades_df["pnl_pct"]
        colors = ["green" if x > 0 else "red" for x in pnl_pcts]

        ax1.bar(range(len(pnl_pcts)), pnl_pcts, color=colors, alpha=0.7)
        ax1.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
        ax1.set_title("거래별 손익률", fontsize=14, fontweight="bold")
        ax1.set_xlabel("거래 번호", fontsize=12)
        ax1.set_ylabel("손익률 (%)", fontsize=12)
        ax1.grid(True, alpha=0.3, axis="y")

        # 2. 손익률 분포
        ax2.hist(pnl_pcts, bins=20, color="#2E86AB", alpha=0.7, edgecolor="black")
        ax2.axvline(x=0, color="red", linestyle="--", linewidth=2)
        ax2.axvline(
            x=pnl_pcts.mean(),
            color="green",
            linestyle="--",
            linewidth=2,
            label=f"평균: {pnl_pcts.mean():.2f}%",
        )
        ax2.set_title("손익률 분포", fontsize=14, fontweight="bold")
        ax2.set_xlabel("손익률 (%)", fontsize=12)
        ax2.set_ylabel("빈도", fontsize=12)
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3, axis="y")

        plt.tight_layout()

        if save and self.output_dir:
            filepath = self.output_dir / "trades_distribution.png"
            plt.savefig(filepath, dpi=300, bbox_inches="tight")
            print(f"✅ 저장: {filepath}")

        if show:
            plt.show()
        else:
            plt.close()

    def plot_monthly_returns(self, save: bool = True, show: bool = False):
        """월별 수익률 히트맵"""
        if self.equity_df.empty:
            print("⚠️  자산 데이터가 없어 월별 수익률을 계산할 수 없습니다.")
            return

        # 월별 수익률 계산
        equity_df = self.equity_df.copy()
        equity_df["year_month"] = equity_df["timestamp"].dt.to_period("M")

        # 각 월의 마지막 equity 값
        monthly = equity_df.groupby("year_month")["equity"].last()
        monthly_returns = monthly.pct_change() * 100

        if len(monthly_returns) < 2:
            print("⚠️  데이터가 부족해 월별 수익률을 계산할 수 없습니다.")
            return

        # 연도와 월로 분리
        years = monthly_returns.index.year.unique()
        months = range(1, 13)

        # 피벗 테이블 생성
        data = []
        for year in years:
            row = []
            for month in months:
                period = pd.Period(f"{year}-{month:02d}", freq="M")
                if period in monthly_returns.index:
                    row.append(monthly_returns[period])
                else:
                    row.append(np.nan)
            data.append(row)

        # numpy array로 변환
        data = np.array(data, dtype=float)

        fig, ax = plt.subplots(figsize=(14, max(4, len(years) * 0.8)))

        # 히트맵 그리기 (NaN은 마스킹됨)
        im = ax.imshow(data, cmap="RdYlGn", aspect="auto", vmin=-10, vmax=10)

        # 축 설정
        ax.set_xticks(range(12))
        ax.set_xticklabels([f"{m}월" for m in months])
        ax.set_yticks(range(len(years)))
        ax.set_yticklabels(years)

        # 값 표시
        for i, year_data in enumerate(data):
            for j, val in enumerate(year_data):
                if not np.isnan(val):
                    text = ax.text(
                        j,
                        i,
                        f"{val:.1f}%",
                        ha="center",
                        va="center",
                        color="black" if abs(val) < 5 else "white",
                        fontsize=9,
                    )

        ax.set_title("월별 수익률", fontsize=16, fontweight="bold")
        plt.colorbar(im, ax=ax, label="수익률 (%)")

        plt.tight_layout()

        if save and self.output_dir:
            filepath = self.output_dir / "monthly_returns.png"
            plt.savefig(filepath, dpi=300, bbox_inches="tight")
            print(f"✅ 저장: {filepath}")

        if show:
            plt.show()
        else:
            plt.close()

    def generate_all_plots(self, save: bool = True, show: bool = False):
        """모든 그래프 생성"""
        print("\n📊 시각화 생성 중...")

        self.plot_equity_curve(save=save, show=show)
        self.plot_drawdown(save=save, show=show)
        self.plot_trades_distribution(save=save, show=show)
        self.plot_monthly_returns(save=save, show=show)

        if save and self.output_dir:
            print(f"\n✅ 모든 그래프가 {self.output_dir}에 저장되었습니다.\n")

    def save_summary_report(self):
        """결과 요약 리포트 저장"""
        if not self.output_dir:
            return

        filepath = self.output_dir / "summary.txt"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"백테스팅 결과 요약: {self.results['strategy_name']}\n")
            f.write("=" * 80 + "\n\n")

            f.write("기본 정보\n")
            f.write("-" * 80 + "\n")
            f.write(f"거래쌍: {self.results['symbol']}\n")
            f.write(f"타임프레임: {self.results['timeframe']}\n")
            f.write(
                f"기간: {self.results['start_date'].strftime('%Y-%m-%d')} ~ "
                f"{self.results['end_date'].strftime('%Y-%m-%d')}\n"
            )
            f.write(f"초기 자본금: ${self.results['initial_capital']:,.2f}\n")
            f.write(f"수수료: {self.results['commission'] * 100:.3f}%\n\n")

            f.write("수익 지표\n")
            f.write("-" * 80 + "\n")
            f.write(f"최종 자본금: ${self.results['final_capital']:,.2f}\n")
            f.write(f"총 수익률: {self.results['total_return']:.2f}%\n")
            f.write(f"최대 낙폭 (MDD): {self.results['max_drawdown']:.2f}%\n")
            f.write(f"샤프 비율: {self.results['sharpe_ratio']:.2f}\n\n")

            f.write("거래 통계\n")
            f.write("-" * 80 + "\n")
            f.write(f"총 거래 횟수: {self.results['total_trades']}\n")
            f.write(f"승리 거래: {self.results['winning_trades']}\n")
            f.write(f"패배 거래: {self.results['losing_trades']}\n")
            f.write(f"승률: {self.results['win_rate']:.2f}%\n\n")

            if self.results["parameters"]:
                f.write("전략 파라미터\n")
                f.write("-" * 80 + "\n")
                for key, value in self.results["parameters"].items():
                    f.write(f"{key}: {value}\n")

        print(f"✅ 요약 리포트 저장: {filepath}")
