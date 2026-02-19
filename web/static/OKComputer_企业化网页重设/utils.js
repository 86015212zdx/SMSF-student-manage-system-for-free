/**
 * API工具函数 - 用于正确构建API请求URL
 * 解决生产环境部署时的URL拼接问题
 */

/**
 * 构建API基础URL
 * @returns {string} 正确格式的API基础URL
 */
function buildApiBaseUrl() {
    // 判断是否为本地开发环境
    const isLocalhost = window.location.hostname === 'localhost' || 
                       window.location.hostname === '127.0.0.1' ||
                       window.location.hostname === '0.0.0.0';
    
    if (isLocalhost) {
        // 本地开发环境，明确使用5000端口
        // 使用正则表达式安全地替换端口号
        return window.location.origin.replace(/:\d*$/, ':5000');
    } else {
        // 生产环境，使用当前域名和端口
        return window.location.origin;
    }
}

/**
 * 构建完整的API URL
 * @param {string} endpoint - API端点路径（如 '/api/study-resources'）
 * @returns {string} 完整的API URL
 */
function buildApiUrl(endpoint) {
    const baseUrl = buildApiBaseUrl();
    // 确保endpoint以/开头
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : '/' + endpoint;
    return baseUrl + cleanEndpoint;
}

/**
 * 测试API连接
 * @param {string} endpoint - API端点
 * @returns {Promise<Object>} 测试结果
 */
async function testApiConnection(endpoint) {
    try {
        const url = buildApiUrl(endpoint);
        console.log(`测试API连接: ${url}`);
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        return {
            success: response.ok,
            status: response.status,
            statusText: response.statusText,
            url: url
        };
    } catch (error) {
        return {
            success: false,
            error: error.message,
            url: buildApiUrl(endpoint)
        };
    }
}

// 导出函数（如果在模块环境中）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        buildApiBaseUrl,
        buildApiUrl,
        testApiConnection
    };
}