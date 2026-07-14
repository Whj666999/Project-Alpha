from pathlib import Path

import pandas as pd


DATA_DIR = Path("data")

POSITIONS = {
    "588200": {
        "name": "科创芯片ETF",
        "shares": 640_100,
        "cost": 4.505,
    },
    "688008": {
        "name": "澜起科技",
        "shares": 14_743,
        "cost": 275.053,
    },
}


def load_history(code: str) -> pd.DataFrame:
    """读取本地历史行情 CSV。"""
    file_path = DATA_DIR / f"{code}.csv"

    if not file_path.exists():
        raise FileNotFoundError(f"找不到数据文件：{file_path}")

    df = pd.read_csv(file_path)

    if df.empty:
        raise ValueError(f"{code} 数据为空")

    required_columns = {"日期", "收盘", "成交量"}

    if not required_columns.issubset(df.columns):
        raise ValueError(
            f"{code} 缺少必要字段，当前字段：{list(df.columns)}"
        )

    df["日期"] = pd.to_datetime(df["日期"])
    df["收盘"] = pd.to_numeric(df["收盘"], errors="coerce")
    df["成交量"] = pd.to_numeric(df["成交量"], errors="coerce")

    df = (
        df.dropna(subset=["收盘", "成交量"])
        .sort_values("日期")
        .reset_index(drop=True)
    )

    if len(df) < 60:
        raise ValueError(f"{code} 数据不足 60 个交易日")

    return df


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """计算均线、成交量均值和 60 日高低点。"""
    result = df.copy()

    result["MA5"] = result["收盘"].rolling(5).mean()
    result["MA20"] = result["收盘"].rolling(20).mean()
    result["MA60"] = result["收盘"].rolling(60).mean()

    result["VOL5"] = result["成交量"].rolling(5).mean()
    result["VOL20"] = result["成交量"].rolling(20).mean()

    result["HIGH60"] = result["收盘"].rolling(60).max()
    result["LOW60"] = result["收盘"].rolling(60).min()

    return result


def get_trend_state(
    price: float,
    ma5: float,
    ma20: float,
    ma60: float,
) -> str:
    """根据价格与均线关系判断趋势状态。"""
    if price > ma5 > ma20 > ma60:
        return "多头排列，趋势偏强"

    if price < ma5 < ma20 < ma60:
        return "空头排列，趋势偏弱"

    if price > ma20:
        return "价格位于20日线上方，偏强震荡"

    return "价格位于20日线下方，偏弱震荡"


def get_volume_state(volume_ratio: float) -> str:
    """根据成交量相对 20 日均量判断资金活跃度。"""
    if volume_ratio >= 2.0:
        return "★★★★★ 极度放量，资金异常活跃"

    if volume_ratio >= 1.5:
        return "★★★★ 明显放量"

    if volume_ratio >= 1.1:
        return "★★★ 温和放量"

    if volume_ratio >= 0.8:
        return "★★ 成交量正常"

    return "★ 明显缩量"


def get_price_position(
    price: float,
    high60: float,
    low60: float,
) -> tuple[float, float, str]:
    """计算当前价格相对 60 日高低点的位置。"""
    distance_to_high = (price / high60 - 1) * 100
    distance_from_low = (price / low60 - 1) * 100

    range_size = high60 - low60

    if range_size <= 0:
        position_pct = 50.0
    else:
        position_pct = (price - low60) / range_size * 100

    if position_pct >= 80:
        position_state = "位于60日区间高位"

    elif position_pct >= 60:
        position_state = "位于60日区间中高位"

    elif position_pct >= 40:
        position_state = "位于60日区间中部"

    elif position_pct >= 20:
        position_state = "位于60日区间中低位"

    else:
        position_state = "位于60日区间低位"

    return distance_to_high, distance_from_low, position_state


def analyze_position(code: str, position: dict) -> dict:
    """分析单只持仓。"""
    df = load_history(code)
    df = calculate_indicators(df)

    latest = df.iloc[-1]

    price = float(latest["收盘"])
    shares = int(position["shares"])
    cost = float(position["cost"])

    ma5 = float(latest["MA5"])
    ma20 = float(latest["MA20"])
    ma60 = float(latest["MA60"])

    today_volume = float(latest["成交量"])
    vol5 = float(latest["VOL5"])
    vol20 = float(latest["VOL20"])

    high60 = float(latest["HIGH60"])
    low60 = float(latest["LOW60"])

    market_value = price * shares
    cost_value = cost * shares
    profit = market_value - cost_value
    profit_pct = (price / cost - 1) * 100

    volume_ratio = today_volume / vol20 if vol20 > 0 else 0.0

    trend_state = get_trend_state(
        price=price,
        ma5=ma5,
        ma20=ma20,
        ma60=ma60,
    )

    volume_state = get_volume_state(volume_ratio)

    (
        distance_to_high,
        distance_from_low,
        position_state,
    ) = get_price_position(
        price=price,
        high60=high60,
        low60=low60,
    )

    return {
        "code": code,
        "name": position["name"],
        "date": latest["日期"].date(),
        "price": price,
        "shares": shares,
        "cost": cost,
        "market_value": market_value,
        "profit": profit,
        "profit_pct": profit_pct,
        "ma5": ma5,
        "ma20": ma20,
        "ma60": ma60,
        "trend_state": trend_state,
        "today_volume": today_volume,
        "vol5": vol5,
        "vol20": vol20,
        "volume_ratio": volume_ratio,
        "volume_state": volume_state,
        "high60": high60,
        "low60": low60,
        "distance_to_high": distance_to_high,
        "distance_from_low": distance_from_low,
        "position_state": position_state,
    }


def print_position_report(result: dict) -> None:
    """打印单只持仓分析报告。"""
    print("\n" + "=" * 60)
    print(f"{result['name']}（{result['code']}）")
    print(f"数据日期：{result['date']}")
    print("-" * 60)

    print("持仓情况")
    print(f"最新收盘：{result['price']:.3f} 元")
    print(f"持仓成本：{result['cost']:.3f} 元")
    print(f"持仓数量：{result['shares']:,} 股")
    print(f"当前市值：{result['market_value']:,.2f} 元")
    print(f"浮动盈亏：{result['profit']:,.2f} 元")
    print(f"盈亏比例：{result['profit_pct']:.2f}%")

    print("-" * 60)
    print("趋势分析")
    print(f"MA5：  {result['ma5']:.3f}")
    print(f"MA20： {result['ma20']:.3f}")
    print(f"MA60： {result['ma60']:.3f}")
    print(f"趋势判断：{result['trend_state']}")

    print("-" * 60)
    print("成交量分析")
    print(f"今日成交量：{result['today_volume']:,.0f}")
    print(f"5日均量：   {result['vol5']:,.0f}")
    print(f"20日均量：  {result['vol20']:,.0f}")
    print(f"成交量倍数：{result['volume_ratio']:.2f} 倍")
    print(f"资金活跃度：{result['volume_state']}")

    print("-" * 60)
    print("60日价格位置")
    print(f"60日最高价：{result['high60']:.3f}")
    print(f"60日最低价：{result['low60']:.3f}")
    print(f"距离60日高点：{result['distance_to_high']:.2f}%")
    print(f"距离60日低点：+{result['distance_from_low']:.2f}%")
    print(f"位置判断：{result['position_state']}")


def print_portfolio_summary(results: list[dict]) -> None:
    """打印组合汇总。"""
    total_market_value = sum(
        item["market_value"] for item in results
    )
    total_cost_value = sum(
        item["cost"] * item["shares"] for item in results
    )
    total_profit = sum(
        item["profit"] for item in results
    )

    total_profit_pct = (
        total_profit / total_cost_value * 100
        if total_cost_value > 0
        else 0.0
    )

    print("\n" + "=" * 60)
    print("组合汇总")
    print(f"组合成本金额：{total_cost_value:,.2f} 元")
    print(f"组合当前市值：{total_market_value:,.2f} 元")
    print(f"组合浮动盈亏：{total_profit:,.2f} 元")
    print(f"组合盈亏比例：{total_profit_pct:.2f}%")
    print("=" * 60)


def main() -> None:
    results: list[dict] = []

    for code, position in POSITIONS.items():
        try:
            result = analyze_position(code, position)
            results.append(result)
            print_position_report(result)

        except Exception as exc:
            print(f"\n{code} 分析失败：{exc}")

    if results:
        print_portfolio_summary(results)
    else:
        print("\n没有可用的持仓分析结果。")


if __name__ == "__main__":
    main()