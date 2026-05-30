import socket
import time
import threading



class ConnectionManager:
    
    def __init__(self):
        # 连接池：{ip: (socket, last_used_time, health_score)}
        self.connection_pool = {}
        # 连接池最大大小
        self.max_pool_size = 20
        # 连接最大空闲时间（秒）
        self.max_idle_time = 30
        # 自适应超时参数
        self.base_connect_timeout = 2.0
        self.base_read_timeout = 3.0
        # 网络状况评分：0-100，越高表示网络越好
        self.network_score = 50
        # 连接健康评分：{ip: health_score}
        self.health_scores = {}
        # 锁，用于线程安全
        self.pool_lock = threading.Lock()
        self.ip_locks = {}
        # 用于创建IP锁时的线程安全
        self.ip_lock_create = threading.Lock()
    def get_connection(self, ip, port=4028, connect_timeout=None, read_timeout=None):
        # 确保当前IP的锁存在（线程安全）
        with self.ip_lock_create:
            if ip not in self.ip_locks:
                self.ip_locks[ip] = threading.Lock()
        with self.ip_locks[ip]:
            # 清理过期连接
            self._cleanup_expired_connections()

            # 计算自适应超时
            if connect_timeout is None:
                connect_timeout = self._get_adaptive_connect_timeout()
            if read_timeout is None:
                read_timeout = self._get_adaptive_read_timeout()
        
        # 尝试从连接池获取
        with self.pool_lock:
            if ip in self.connection_pool:
                sock, last_used, health_score = self.connection_pool[ip]
                # 检查连接是否仍然可用
                if self._is_connection_alive(sock):
                    # 更新最后使用时间
                    self.connection_pool[ip] = (sock, time.time(), health_score)
                    return sock, False, (connect_timeout, read_timeout)
                else:
                    # 连接已失效，从池中移除
                    try:
                        sock.close()
                    except:
                        pass
                    del self.connection_pool[ip]
        
        # 创建新连接
        sock = self._create_new_connection(ip, port, connect_timeout)
        if sock:
            # 将新连接加入连接池（如果池未满）
            with self.pool_lock:
                if len(self.connection_pool) < self.max_pool_size:
                    self.connection_pool[ip] = (sock, time.time(), 100)  # 初始健康评分100
            return sock, True, (connect_timeout, read_timeout)
        
        return None, True, (connect_timeout, read_timeout)
    
    def return_connection(self, ip, sock, success=True):
        if sock is None:
            return
        # 同一IP的归还操作也需要串行（避免与get_connection冲突）
        with self.ip_locks.get(ip, threading.Lock()):  # 防止ip未在锁字典中的极端情况
            # 更新网络状况评分
            self._update_network_score(success)
        
            # 更新连接健康评分
            health_score = self.health_scores.get(ip, 100)
            if success:
                # 成功使用，提高健康评分
                health_score = min(100, health_score + 10)
            else:
                # 使用失败，降低健康评分
                health_score = max(0, health_score - 30)
            
            self.health_scores[ip] = health_score
            
            # 如果连接健康评分过低，关闭连接
            if health_score < 30:
                try:
                    sock.close()
                except:
                    pass
                with self.pool_lock:
                    if ip in self.connection_pool:
                        del self.connection_pool[ip]
                return
            
            # 归还到连接池
            with self.pool_lock:
                if ip in self.connection_pool:
                    self.connection_pool[ip] = (sock, time.time(), health_score)
    
    def close_connection(self, ip, sock):
        """关闭连接并从连接池中移除"""
        if sock:
            try:
                sock.close()
            except:
                pass
        # 加锁确保删除操作安全
        with self.ip_locks.get(ip, threading.Lock()):
            with self.pool_lock:
                if ip in self.connection_pool:
                    del self.connection_pool[ip]
    
    def _create_new_connection(self, ip, port, connect_timeout):
        """创建新连接"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(connect_timeout)
            sock.connect((ip, port))
            return sock
        except Exception as e:
            # 连接失败，降低网络评分
            self._update_network_score(False)
            try:
                sock.close()
            except:
                pass
            return None
    
    def _is_connection_alive(self, sock):
        """检查连接是否仍然存活"""
        if sock is None:
            return False
        
        try:
            # 尝试发送一个空数据包来检查连接状态
            sock.settimeout(0.1)
            sock.send(b'')
            return True
        except:
            return False
    
    def _cleanup_expired_connections(self):
        """清理过期连接"""
        current_time = time.time()
        expired_ips = []
        
        with self.pool_lock:
            for ip, (sock, last_used, health_score) in self.connection_pool.items():
                # 检查连接是否空闲时间过长
                if current_time - last_used > self.max_idle_time:
                    expired_ips.append(ip)
                # 检查连接健康评分过低
                elif health_score < 20:
                    expired_ips.append(ip)
            
            # 关闭并移除过期连接
            for ip in expired_ips:
                sock, _, _ = self.connection_pool[ip]
                try:
                    sock.close()
                except:
                    pass
                del self.connection_pool[ip]
    
    def _get_adaptive_connect_timeout(self):
        """获取自适应连接超时"""
        # 根据网络评分调整超时
        # 网络越好，超时越短；网络越差，超时越长
        factor = max(0.5, min(2.0, 2.0 - self.network_score / 100))
        return self.base_connect_timeout * factor
    
    def _get_adaptive_read_timeout(self):
        """获取自适应读取超时"""
        # 根据网络评分调整超时
        factor = max(0.5, min(2.0, 2.0 - self.network_score / 100))
        return self.base_read_timeout * factor
    
    def _update_network_score(self, success):
        """更新网络状况评分"""
        if success:
            # 成功操作，提高网络评分
            self.network_score = min(100, self.network_score + 2)
        else:
            # 失败操作，降低网络评分
            self.network_score = max(10, self.network_score - 5)
        
        # 网络评分随时间缓慢恢复
        self.network_score = min(100, self.network_score + 0.1)
    
    def get_network_status(self):
        """获取网络状态描述"""
        if self.network_score >= 80:
            return "优秀"
        elif self.network_score >= 60:
            return "良好"
        elif self.network_score >= 40:
            return "一般"
        elif self.network_score >= 20:
            return "较差"
        else:
            return "极差"
    
    def get_pool_stats(self):
        """获取连接池统计信息"""
        with self.pool_lock:
            pool_size = len(self.connection_pool)
            avg_health = sum(score for _, _, score in self.connection_pool.values()) / pool_size if pool_size > 0 else 0
        
        return {
            "pool_size": pool_size,
            "max_pool_size": self.max_pool_size,
            "avg_health_score": avg_health,
            "network_score": self.network_score,
            "network_status": self.get_network_status(),
            "adaptive_connect_timeout": self._get_adaptive_connect_timeout(),
            "adaptive_read_timeout": self._get_adaptive_read_timeout()
        }