import concurrent.futures
import requests
import time
import statistics

# url = "http://0.0.0.0:8080/api/v1/config/3"
url = "http://0.0.0.0:8085/api/v1/common/demo/1"


def send_request(thread_id):
    start_time = time.time()
    try:
        response = requests.get(url, timeout=30)
        elapsed_time = (time.time() - start_time) * 1000  # 毫秒

        if response.status_code == 200:
            return {"status": "success", "time": elapsed_time, "thread_id": thread_id,
                    "status_code": response.status_code}
        else:
            return {"status": "fail", "time": elapsed_time, "thread_id": thread_id, "status_code": response.status_code}

    except Exception as e:
        elapsed_time = (time.time() - start_time) * 1000
        return {"status": "error", "time": elapsed_time, "thread_id": thread_id, "error": str(e)}


def run_concurrent_test(num_requests=100, max_workers=100):
    print(f"开始并发测试，请求数: {num_requests}, 最大并发数: {max_workers}")
    print("=" * 60)

    start_time = time.time()
    response_times = []
    success_count = 0
    fail_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        futures = [executor.submit(send_request, i + 1) for i in range(num_requests)]

        # 收集结果
        for future in concurrent.futures.as_completed(futures):
            result = future.result()

            if result["status"] == "success":
                success_count += 1
                response_times.append(result["time"])
                print(f"线程 {result['thread_id']:3d} 成功 | 耗时: {result['time']:6.2f}ms")
            else:
                fail_count += 1
                error_msg = result.get('error', f"状态码: {result.get('status_code', 'N/A')}")
                print(f"线程 {result['thread_id']:3d} 失败 | {error_msg} | 耗时: {result['time']:6.2f}ms")

    total_elapsed = time.time() - start_time  # 总耗时（秒）

    # 输出统计结果
    print("=" * 60)
    print("测试结果统计:")
    print(f"总请求数: {num_requests}")
    print(f"成功请求: {success_count}")
    print(f"失败请求: {fail_count}")
    print(f"总耗时: {total_elapsed:.2f} 秒")
    print(f"总耗时: {total_elapsed * 1000:.2f} 毫秒")  # 也显示毫秒版本

    if response_times:
        print(f"平均响应时间: {statistics.mean(response_times):.2f}ms")
        print(f"最小响应时间: {min(response_times):.2f}ms")
        print(f"最大响应时间: {max(response_times):.2f}ms")

        # ✅ 正确的 QPS 计算
        if total_elapsed > 0:
            qps = success_count / total_elapsed
            print(f"QPS: {qps:.2f}")
        else:
            print("QPS: 无限大（耗时几乎为0）")


if __name__ == "__main__":
    run_concurrent_test(num_requests=1000, max_workers=2000)