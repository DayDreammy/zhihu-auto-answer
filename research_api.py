#!/usr/bin/env python3
"""
知乎API研究 - 尝试直接调用知乎接口获取邀请列表
"""
import requests
import json
from pathlib import Path


class ZhihuAPIResearch:
    """研究知乎API接口"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.zhihu.com/',
        })
    
    def load_cookies(self, cookie_file='zhihu_cookies.json'):
        """加载cookie文件"""
        if not Path(cookie_file).exists():
            print(f"❌ Cookie文件不存在: {cookie_file}")
            return False
        
        try:
            cookies = json.loads(Path(cookie_file).read_text())
            for cookie in cookies:
                self.session.cookies.set(
                    cookie['name'],
                    cookie['value'],
                    domain=cookie.get('domain', '.zhihu.com')
                )
            print(f"✅ 已加载 {len(cookies)} 个cookie")
            return True
        except Exception as e:
            print(f"❌ 加载cookie失败: {e}")
            return False
    
    def test_api_endpoints(self):
        """测试可能的API端点"""
        
        # 可能的通知/邀请API端点
        endpoints = [
            # 通知列表
            ('GET', 'https://www.zhihu.com/api/v4/notifications'),
            ('GET', 'https://www.zhihu.com/api/v4/notifications/v2'),
            ('GET', 'https://www.zhihu.com/api/v4/messages'),
            
            # 用户相关
            ('GET', 'https://www.zhihu.com/api/v4/me'),
            ('GET', 'https://www.zhihu.com/api/v4/me/invitations'),
            ('GET', 'https://www.zhihu.com/api/v4/mine/invitations'),
            
            # 问题和回答
            ('GET', 'https://www.zhihu.com/api/v4/questions/invited'),
        ]
        
        results = []
        
        print("\n测试知乎API端点...")
        print("=" * 60)
        
        for method, url in endpoints:
            try:
                print(f"\n测试: {method} {url}")
                response = self.session.request(method, url, timeout=10)
                
                status = response.status_code
                content_type = response.headers.get('content-type', 'unknown')
                
                result = {
                    'url': url,
                    'method': method,
                    'status': status,
                    'content_type': content_type,
                }
                
                if status == 200:
                    print(f"  ✅ 成功 (200)")
                    
                    # 尝试解析JSON
                    if 'json' in content_type:
                        try:
                            data = response.json()
                            result['data'] = data
                            
                            # 分析数据结构
                            if isinstance(data, dict):
                                if 'data' in data:
                                    items = data['data']
                                    print(f"  📊 返回 {len(items) if isinstance(items, list) else 'object'} 条数据")
                                    
                                    # 检查是否包含邀请相关内容
                                    if isinstance(items, list) and len(items) > 0:
                                        sample = json.dumps(items[0], ensure_ascii=False)[:200]
                                        print(f"  📝 样本: {sample}...")
                                else:
                                    print(f"  📊 返回 keys: {list(data.keys())[:5]}")
                        except:
                            result['text_preview'] = response.text[:500]
                    else:
                        result['text_preview'] = response.text[:500]
                        
                elif status == 401:
                    print(f"  ❌ 未授权 (401) - 需要登录")
                    result['error'] = 'Unauthorized'
                elif status == 404:
                    print(f"  ❌ 不存在 (404)")
                    result['error'] = 'Not found'
                else:
                    print(f"  ⚠️ 状态码: {status}")
                    result['error'] = f'Status {status}'
                
                results.append(result)
                
            except Exception as e:
                print(f"  ❌ 请求失败: {e}")
                results.append({
                    'url': url,
                    'method': method,
                    'error': str(e)
                })
        
        # 保存结果
        Path('api_research_results.json').write_text(
            json.dumps(results, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        print("\n" + "=" * 60)
        print("测试结果已保存到 api_research_results.json")
        
        return results
    
    def analyze_invitation_structure(self):
        """分析邀请数据结构（如果有的话）"""
        results_file = Path('api_research_results.json')
        if not results_file.exists():
            print("❌ 没有找到测试结果文件")
            return
        
        results = json.loads(results_file.read_text())
        
        print("\n分析邀请相关接口...")
        print("=" * 60)
        
        for result in results:
            if result.get('status') == 200:
                url = result['url']
                data = result.get('data')
                
                if 'invitation' in url.lower() or 'invite' in url.lower():
                    print(f"\n📌 可能的邀请接口: {url}")
                    if isinstance(data, dict) and 'data' in data:
                        items = data['data']
                        if isinstance(items, list):
                            print(f"   包含 {len(items)} 个邀请")
                            if len(items) > 0:
                                print(f"   样本结构:")
                                print(json.dumps(items[0], indent=2, ensure_ascii=False)[:500])


if __name__ == '__main__':
    import sys
    
    researcher = ZhihuAPIResearch()
    
    # 检查是否有cookie文件
    if len(sys.argv) > 1:
        cookie_file = sys.argv[1]
    else:
        cookie_file = 'zhihu_cookies.json'
    
    if Path(cookie_file).exists():
        researcher.load_cookies(cookie_file)
    else:
        print(f"⚠️ 未找到cookie文件: {cookie_file}")
        print("将使用空cookie测试（大部分API会返回401）")
    
    # 运行测试
    researcher.test_api_endpoints()
    researcher.analyze_invitation_structure()
