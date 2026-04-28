#!/usr/bin/env python3
"""测试路由是否能正常加载"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.main import app
    print("✅ 主应用加载成功！")
    
    # 打印所有路由
    print("\n📋 可用的路由列表:")
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = ', '.join(route.methods)
            print(f"  {methods:15} {route.path}")
            
    print("\n✅ 所有路由加载成功！")
    
except Exception as e:
    print(f"❌ 错误: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
