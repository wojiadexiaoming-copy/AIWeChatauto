'use strict';

const db = uniCloud.database();
const dbCmd = db.command;

exports.main = async (event, context) => {
	const corsHeaders = {
		'Access-Control-Allow-Origin': '*',
		'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
		'Access-Control-Allow-Headers': 'Authorization, Content-Type',
	};

	// CORS preflight
	if (event.httpMethod === 'OPTIONS') {
		return { statusCode: 200, headers: corsHeaders, body: '' };
	}

	const clientIp = context.CLIENTIP || event.clientIP || '';
	
	// Rate Limit check (max 15 requests per IP per 24 hours)
	let allowed = true;
	if (clientIp) {
		const now = new Date();
		const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString();
		try {
			const countRes = await db.collection('ai_tools_logs')
				.where({
					ip: clientIp,
					timestamp: dbCmd.gt(oneDayAgo)
				})
				.count();
			
			const count = countRes.result || countRes.total || 0;
			if (count >= 15) {
				allowed = false;
			} else {
				await db.collection('ai_tools_logs').add({
					ip: clientIp,
					timestamp: now.toISOString()
				});
				
				// Clean up old logs asynchronously to keep DB clean
				db.collection('ai_tools_logs')
					.where({
						timestamp: dbCmd.lt(oneDayAgo)
					})
					.remove()
					.catch(e => console.error('Old logs cleanup failed:', e));
			}
		} catch (e) {
			console.warn('Rate limit DB check skipped (e.g. collection not created). Error:', e.message);
			// Fallback to allow request if DB isn't fully configured for log collection yet
		}
	}

	if (!allowed) {
		return {
			statusCode: 429,
			headers: { ...corsHeaders, 'Content-Type': 'application/json' },
			body: JSON.stringify({ success: false, message: '请求过于频繁，请稍后再试（24小时内限制15次）' }),
		};
	}

	try {
		// Fetch all tools from database using cursor pagination (limit 1000 per query in cloud functions)
		let allTools = [];
		let skip = 0;
		const limit = 1000;
		while (true) {
			const res = await db.collection('ai_tools').skip(skip).limit(limit).get();
			if (!res.data || res.data.length === 0) {
				break;
			}
			allTools = allTools.concat(res.data);
			if (res.data.length < limit) {
				break;
			}
			skip += limit;
		}

		return {
			statusCode: 200,
			headers: { ...corsHeaders, 'Content-Type': 'application/json' },
			body: JSON.stringify({ success: true, count: allTools.length, data: allTools }),
		};
	} catch (e) {
		console.error('Fetch ai_tools error:', e);
		return {
			statusCode: 500,
			headers: { ...corsHeaders, 'Content-Type': 'application/json' },
			body: JSON.stringify({ success: false, message: '获取云端数据库工具列表失败: ' + e.message }),
		};
	}
};
