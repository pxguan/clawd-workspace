#!/usr/bin/env python3
"""
A股监控脚本 - 使用QVeris API获取股票数据并分析
每15分钟运行一次
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path

# 配置
QVERIS_API_KEY = os.getenv("QVERIS_API_KEY", "sk-mcKudIlefQjypdf8_Sk7zmFdVD_5j3sP154THWvy9Y4")
QVERIS_BASE = "https://api.qveris.ai/v1"
LOG_DIR = Path("/home/node/clawd/memory/a-stocks")
LOG_FILE = LOG_DIR / "monitor.log"
STATE_FILE = LOG_DIR / "latest_recommendations.json"

LOG_DIR.mkdir(parents=True, exist_ok=True)


def log(message: str):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")


def get_qveris_data(tool: str, params: dict) -> dict:
    """调用QVeris API获取数据"""
    try:
        response = requests.post(
            f"{QVERIS_BASE}/tools/execute",
            headers={
                "Authorization": f"Bearer {QVERIS_API_KEY}",
                "Content-Type": "application/json"
            },
            json={"tool": tool, "params": params},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log(f"QVeris API调用失败: {e}")
        return None


def get_a_stock_movers() -> list:
    """获取A股涨跌幅较大的股票"""
    log("获取A股涨跌数据...")

    # QVeris可能有多种方式获取股票数据
    # 这里尝试不同的工具
    tools_to_try = [
        {"tool": "stock.cn_movers", "params": {"limit": 30}},
        {"tool": "stock_market.get_movers", "params": {"market": "CN", "limit": 30}},
        {"tool": "finance.stock_movers", "params": {"region": "CN", "limit": 30}},
    ]

    for tool_config in tools_to_try:
        result = get_qveris_data(tool_config["tool"], tool_config["params"])
        if result and result.get("data") or result.get("results"):
            log(f"成功使用工具: {tool_config['tool']}")
            return result.get("data", result.get("results", []))

    log("所有工具都失败，尝试备用方案...")
    return []


def analyze_stock_potential(stock_data: list) -> list:
    """分析股票增长潜力"""
    log("分析股票潜力...")

    if not stock_data:
        return []

    # 筛选条件
    candidates = []

    for stock in stock_data:
        try:
            symbol = stock.get("symbol", stock.get("code", ""))
            name = stock.get("name", stock.get("title", ""))
            change_pct = float(stock.get("change_percent", stock.get("change_pct", 0)))
            volume = stock.get("volume", stock.get("vol", 0))

            if not symbol:
                continue

            # 基本筛选：涨幅>2% 或 跌幅>3%（超跌反弹机会）
            if change_pct > 2 or change_pct < -3:
                candidates.append({
                    "symbol": symbol,
                    "name": name,
                    "change_pct": change_pct,
                    "volume": volume,
                    "score": calculate_potential_score(stock)
                })

        except (ValueError, KeyError) as e:
            continue

    # 按潜力分数排序，取前3
    candidates.sort(key=lambda x: x["score"], reverse=True)
    top_3 = candidates[:3]

    for i, stock in enumerate(top_3, 1):
        log(f"#{i} {stock['symbol']} ({stock['name']}) - 涨跌: {stock['change_pct']:.2f}% - 潜力分: {stock['score']}")

    return top_3


def calculate_potential_score(stock: dict) -> float:
    """计算股票潜力分数"""
    score = 0

    try:
        change_pct = float(stock.get("change_percent", stock.get("change_pct", 0)))
        volume = stock.get("volume", stock.get("vol", 1))

        # 涨幅因子（适度上涨更好，避免追高）
        if 2 <= change_pct <= 7:
            score += 40
        elif 7 < change_pct <= 10:
            score += 25
        elif change_pct > 10:
            score += 10  # 涨太多风险大

        # 超跌反弹机会
        elif -8 <= change_pct <= -3:
            score += 30
        elif change_pct < -8:
            score += 15

        # 成交量因子（放量上涨更好）
        if volume > 0:
            score += min(30, volume / 1000000 * 10)

        # 其他因子可以加在这里

    except (ValueError, KeyError):
        pass

    return score


def save_recommendations(recommendations: list):
    """保存推荐结果"""
    result = {
        "timestamp": datetime.now().isoformat(),
        "recommendations": recommendations
    }

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def main():
    """主函数"""
    log("=== A股监控开始 ===")

    # 1. 获取涨跌数据
    stock_data = get_a_stock_movers()

    if not stock_data:
        log("未能获取股票数据，尝试使用备用数据源...")
        # 这里可以添加备用数据源，比如直接爬东方财富等
        log("暂无数据，本次监控结束")
        return

    log(f"获取到 {len(stock_data)} 只股票数据")

    # 2. 分析潜力
    recommendations = analyze_stock_potential(stock_data)

    # 3. 保存结果
    save_recommendations(recommendations)

    log(f"=== 监控完成，推荐 {len(recommendations)} 只股票 ===")

    # 返回结果供外部使用
    return recommendations


if __name__ == "__main__":
    main()
