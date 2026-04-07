"""
数据分析脚本 - 直接查询数据库进行数据分析
无需创建API接口，本地运行即可查看统计结果
"""
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

# 添加backend到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
import pandas as pd

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'backend', 'app.db')

def get_db_session():
    """获取数据库会话"""
    engine = create_engine(f'sqlite:///{DB_PATH}')
    Session = sessionmaker(bind=engine)
    return Session()


def analyze_user_growth(days=30):
    """用户增长分析"""
    print("\n" + "="*50)
    print("📊 用户增长分析")
    print("="*50)
    
    db = get_db_session()
    
    # 查询每日新增用户
    result = db.execute("""
        SELECT 
            date(created_at) as date,
            COUNT(*) as new_users
        FROM users
        WHERE created_at >= date('now', '-{} days')
        GROUP BY date(created_at)
        ORDER BY date DESC
    """.format(days))
    
    df = pd.DataFrame(result.fetchall(), columns=['date', 'new_users'])
    
    if df.empty:
        print("暂无用户数据")
        return
    
    print(f"\n最近{days}天用户增长:")
    print(df.to_string(index=False))
    print(f"\n总计新增用户: {df['new_users'].sum()}")
    print(f"日均新增: {df['new_users'].mean():.1f}")


def analyze_feature_usage(days=7):
    """功能使用分析"""
    print("\n" + "="*50)
    print("🔥 功能使用热度排行")
    print("="*50)
    
    db = get_db_session()
    
    result = db.execute("""
        SELECT 
            event_name,
            COUNT(*) as total_count,
            COUNT(DISTINCT user_id) as unique_users
        FROM event_logs
        WHERE created_at >= date('now', '-{} days')
        GROUP BY event_name
        ORDER BY total_count DESC
    """.format(days))
    
    df = pd.DataFrame(result.fetchall(), 
                      columns=['功能', '总次数', '独立用户'])
    
    if df.empty:
        print("暂无事件数据")
        return
    
    print(f"\n最近{days}天功能使用统计:")
    print(df.to_string(index=False))


def analyze_user_activity():
    """用户活跃度分析 (DAU/WAU/MAU)"""
    print("\n" + "="*50)
    print("👥 用户活跃度分析")
    print("="*50)
    
    db = get_db_session()
    
    result = db.execute("""
        SELECT 
            COUNT(DISTINCT CASE WHEN date(created_at) = date('now') THEN user_id END) as DAU,
            COUNT(DISTINCT CASE WHEN created_at >= date('now', '-7 days') THEN user_id END) as WAU,
            COUNT(DISTINCT CASE WHEN created_at >= date('now', '-30 days') THEN user_id END) as MAU,
            (SELECT COUNT(*) FROM users) as total_users
        FROM event_logs
    """)
    
    row = result.fetchone()
    
    print(f"\n当前活跃用户:")
    print(f"  DAU (日活): {row.DAU}")
    print(f"  WAU (周活): {row.WAU}")
    print(f"  MAU (月活): {row.MAU}")
    print(f"  总用户数:   {row.total_users}")
    
    if row.MAU > 0:
        print(f"\n用户粘性指标:")
        print(f"  DAU/MAU 比率: {row.DAU/row.MAU*100:.1f}%")
        print(f"  月活跃率: {row.MAU/row.total_users*100:.1f}%" if row.total_users > 0 else "")


def analyze_daily_trend(metric_type='chat_count', days=30):
    """分析每日指标趋势"""
    print("\n" + "="*50)
    print(f"📈 {metric_type} 趋势分析")
    print("="*50)
    
    db = get_db_session()
    
    result = db.execute("""
        SELECT 
            metric_date as date,
            SUM(metric_value) as total
        FROM business_metrics
        WHERE metric_type = '{}'
            AND metric_date >= date('now', '-{} days')
        GROUP BY metric_date
        ORDER BY metric_date DESC
    """.format(metric_type, days))
    
    df = pd.DataFrame(result.fetchall(), columns=['date', 'value'])
    
    if df.empty:
        print(f"暂无 {metric_type} 数据")
        return
    
    print(f"\n最近{days}天趋势:")
    print(df.to_string(index=False))
    print(f"\n总计: {df['value'].sum()}")
    print(f"日均: {df['value'].mean():.1f}")
    print(f"峰值: {df['value'].max()} ({df.loc[df['value'].idxmax(), 'date']})")


def analyze_user_retention():
    """用户留存分析（简化版）"""
    print("\n" + "="*50)
    print("🔄 用户留存分析")
    print("="*50)
    
    db = get_db_session()
    
    # 查询最近7天的新用户留存
    result = db.execute("""
        WITH new_users AS (
            SELECT 
                id,
                date(created_at) as reg_date
            FROM users
            WHERE created_at >= date('now', '-7 days')
        )
        SELECT 
            n.reg_date,
            COUNT(DISTINCT n.id) as new_users,
            COUNT(DISTINCT CASE WHEN date(e.created_at) = n.reg_date THEN e.user_id END) as day0_active,
            COUNT(DISTINCT CASE WHEN date(e.created_at) = date(n.reg_date, '+1 day') THEN e.user_id END) as day1_active
        FROM new_users n
        LEFT JOIN event_logs e ON n.id = e.user_id
        GROUP BY n.reg_date
        ORDER BY n.reg_date DESC
    """)
    
    rows = result.fetchall()
    
    if not rows:
        print("暂无留存数据")
        return
    
    print("\n最近7天新用户留存:")
    print(f"{'日期':<12} {'新增':>6} {'当日活跃':>8} {'次日留存':>8}")
    print("-" * 40)
    
    for row in rows:
        day1_retention = f"{row.day1_active/row.new_users*100:.1f}%" if row.new_users > 0 else "N/A"
        print(f"{row.reg_date:<12} {row.new_users:>6} {row.day0_active:>8} {day1_retention:>8}")


def export_to_excel():
    """导出数据到Excel"""
    print("\n" + "="*50)
    print("📁 导出数据到Excel")
    print("="*50)
    
    engine = create_engine(f'sqlite:///{DB_PATH}')
    
    # 导出各表数据
    tables = ['event_logs', 'business_metrics', 'users']
    
    for table in tables:
        try:
            df = pd.read_sql(f"SELECT * FROM {table}", engine)
            filename = f"analysis_{table}.xlsx"
            df.to_excel(filename, index=False)
            print(f"✅ 已导出: {filename} ({len(df)} 条记录)")
        except Exception as e:
            print(f"❌ 导出 {table} 失败: {e}")


def show_menu():
    """显示菜单"""
    print("\n" + "="*50)
    print("📊 数据分析工具")
    print("="*50)
    print("1. 用户增长分析")
    print("2. 功能使用热度")
    print("3. 用户活跃度 (DAU/WAU/MAU)")
    print("4. 每日指标趋势")
    print("5. 用户留存分析")
    print("6. 导出数据到Excel")
    print("7. 运行全部分析")
    print("0. 退出")
    print("="*50)


def main():
    """主函数"""
    if not os.path.exists(DB_PATH):
        print(f"❌ 数据库不存在: {DB_PATH}")
        print("请确保后端服务已运行并生成了数据库")
        return
    
    while True:
        show_menu()
        choice = input("\n请选择功能 (0-7): ").strip()
        
        if choice == '1':
            days = input("查询天数 (默认30): ").strip()
            analyze_user_growth(int(days) if days else 30)
        elif choice == '2':
            days = input("查询天数 (默认7): ").strip()
            analyze_feature_usage(int(days) if days else 7)
        elif choice == '3':
            analyze_user_activity()
        elif choice == '4':
            print("\n可选指标: chat_count, upload_count, review_count, chart_count, user_count")
            metric = input("请输入指标类型 (默认chat_count): ").strip()
            days = input("查询天数 (默认30): ").strip()
            analyze_daily_trend(metric or 'chat_count', int(days) if days else 30)
        elif choice == '5':
            analyze_user_retention()
        elif choice == '6':
            export_to_excel()
        elif choice == '7':
            analyze_user_growth(30)
            analyze_feature_usage(7)
            analyze_user_activity()
            analyze_daily_trend('chat_count', 30)
            analyze_user_retention()
        elif choice == '0':
            print("👋 再见!")
            break
        else:
            print("❌ 无效选择")
        
        input("\n按回车继续...")


if __name__ == '__main__':
    main()
