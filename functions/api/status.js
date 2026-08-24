/**
 * Cloudflare Pages Function: /api/status
 * Queries Turso via HTTP and caches the aggregated 30-day timeline at the global edge.
 */

const SERVICE_META = {
  outline: {
    name: 'Outline',
    category: 'VPS Core',
    description: 'Internal Knowledge Base & Wiki',
    type: 'http'
  },
  crm: {
    name: 'CRM',
    category: 'VPS Core',
    description: 'Customer Relationship Management System',
    type: 'http'
  }
};

function aggregateChecks(rawRows, daysCount = 30) {
  const now = new Date();
  const dayDates = [];
  for (let i = daysCount - 1; i >= 0; i--) {
    const d = new Date(now.getTime() - i * 86400000);
    dayDates.push(d.toISOString().split('T')[0]);
  }

  // Parse raw rows from Turso
  const checksByService = {};
  for (const row of rawRows) {
    const srvId = row[0]?.value;
    const srvName = row[1]?.value;
    const status = row[2]?.value;
    const latency = Number(row[3]?.value) || 0;
    const statusCode = row[4]?.value ? Number(row[4].value) : 200;
    const msg = row[5]?.value || 'HTTP 200';
    const ts = row[6]?.value;

    if (!srvId) continue;

    if (!checksByService[srvId]) {
      checksByService[srvId] = {
        name: srvName,
        checks: []
      };
    }
    checksByService[srvId].checks.push({
      status,
      latency,
      status_code: statusCode,
      msg,
      timestamp: ts
    });
  }

  // Ensure all configured services exist
  for (const [id, meta] of Object.entries(SERVICE_META)) {
    if (!checksByService[id]) {
      checksByService[id] = { name: meta.name, checks: [] };
    }
  }

  const services = [];
  let overallDegradedCount = 0;
  let overallDownCount = 0;

  for (const [srvId, srvData] of Object.entries(checksByService)) {
    const meta = SERVICE_META[srvId] || {
      name: srvData.name || srvId,
      category: 'General Services',
      description: '',
      type: 'http'
    };

    const dayMap = {};
    for (const d of dayDates) {
      dayMap[d] = {
        date: d,
        status: 'nodata',
        uptime_percentage: 100.0,
        avg_latency_ms: 0.0,
        min_latency_ms: 0.0,
        max_latency_ms: 0.0,
        total_checks: 0,
        down_checks: 0,
        degraded_checks: 0,
        operational_checks: 0,
        total_latency: 0.0,
        hours: Array.from({ length: 24 }, (_, h) => ({
          hour: h,
          status: 'nodata',
          avg_latency_ms: 0.0,
          min_latency_ms: 0.0,
          max_latency_ms: 0.0,
          checks_count: 0,
          down_checks: 0,
          degraded_checks: 0,
          operational_checks: 0,
          total_latency: 0.0,
          checks: []
        }))
      };
    }

    let totalScore = 0.0;
    const totalChecks = srvData.checks.length;
    const latestCheck = totalChecks > 0 ? srvData.checks[totalChecks - 1] : null;

    for (const c of srvData.checks) {
      if (!c.timestamp) continue;
      const dateStr = c.timestamp.split('T')[0];
      const day = dayMap[dateStr];
      if (!day) continue;

      day.total_checks++;
      day.total_latency += c.latency;
      if (day.min_latency_ms === 0 || c.latency < day.min_latency_ms) {
        day.min_latency_ms = Math.round(c.latency * 100) / 100;
      }
      if (c.latency > day.max_latency_ms) {
        day.max_latency_ms = Math.round(c.latency * 100) / 100;
      }

      if (c.status === 'operational') {
        day.operational_checks++;
        totalScore += 1.0;
      } else if (c.status === 'degraded') {
        day.degraded_checks++;
        totalScore += 0.5;
      } else {
        day.down_checks++;
      }

      // Hour slot calculation
      try {
        const timePart = c.timestamp.includes('T') ? c.timestamp.split('T')[1] : c.timestamp.split(' ')[1];
        const hour = parseInt(timePart.split(':')[0], 10);
        if (hour >= 0 && hour <= 23) {
          const hMetric = day.hours[hour];
          hMetric.checks_count++;
          hMetric.total_latency += c.latency;
          if (hMetric.min_latency_ms === 0 || c.latency < hMetric.min_latency_ms) {
            hMetric.min_latency_ms = Math.round(c.latency * 100) / 100;
          }
          if (c.latency > hMetric.max_latency_ms) {
            hMetric.max_latency_ms = Math.round(c.latency * 100) / 100;
          }
          if (c.status === 'operational') hMetric.operational_checks++;
          else if (c.status === 'degraded') hMetric.degraded_checks++;
          else hMetric.down_checks++;

          hMetric.checks.push({
            timestamp: c.timestamp,
            latency_ms: Math.round(c.latency * 100) / 100,
            status: c.status,
            status_code: c.status_code,
            message: c.msg
          });
        }
      } catch (e) {}
    }

    const history = dayDates.map((d) => {
      const day = dayMap[d];
      if (day.total_checks > 0) {
        day.avg_latency_ms = Math.round((day.total_latency / day.total_checks) * 100) / 100;
        const dayScore = day.operational_checks * 1.0 + day.degraded_checks * 0.5;
        day.uptime_percentage = Math.round((dayScore / day.total_checks) * 10000) / 100;
        if (day.down_checks === 0 && day.degraded_checks === 0) {
          day.status = 'operational';
        } else if (day.down_checks / day.total_checks > 0.25) {
          day.status = 'down';
        } else {
          day.status = 'degraded';
        }
      }

      day.hours = day.hours.map((h) => {
        if (h.checks_count > 0) {
          h.avg_latency_ms = Math.round((h.total_latency / h.checks_count) * 100) / 100;
          if (h.down_checks === 0 && h.degraded_checks === 0) {
            h.status = 'operational';
          } else if (h.down_checks / h.checks_count > 0.25) {
            h.status = 'down';
          } else {
            h.status = 'degraded';
          }
        }
        delete h.total_latency;
        delete h.operational_checks;
        return h;
      });

      delete day.total_latency;
      delete day.operational_checks;
      return day;
    });

    const uptimePct = totalChecks > 0 ? Math.round((totalScore / totalChecks) * 10000) / 100 : 100.0;
    const currentStatus = latestCheck ? latestCheck.status : 'operational';
    if (currentStatus === 'down') overallDownCount++;
    else if (currentStatus === 'degraded') overallDegradedCount++;

    services.push({
      id: srvId,
      name: meta.name,
      category: meta.category,
      description: meta.description,
      type: meta.type,
      current_status: currentStatus,
      current_latency_ms: latestCheck ? Math.round(latestCheck.latency * 100) / 100 : 0.0,
      current_message: latestCheck ? latestCheck.msg : 'HTTP 200',
      uptime_percentage: uptimePct,
      uptime_30d_percentage: uptimePct,
      uptime_90d_percentage: uptimePct,
      history
    });
  }

  let overallStatus = 'operational';
  if (overallDownCount > 0) overallStatus = 'major_outage';
  else if (overallDegradedCount > 0) overallStatus = 'degraded';

  return {
    title: 'System Status',
    description: 'Live operational status of VPS and Cloud infrastructure',
    last_updated: now.toISOString(),
    overall_status: overallStatus,
    history_days: daysCount,
    services
  };
}

export async function onRequestGet(context) {
  // 1. Edge Cache match
  const cache = caches.default;
  const cacheKey = new Request(context.request.url, context.request);
  let cached = await cache.match(cacheKey);
  if (cached) {
    return cached;
  }

  const { env } = context;
  const rawUrl = env.TURSO_DATABASE_URL || '';
  const token = env.TURSO_AUTH_TOKEN || '';

  if (!rawUrl || !token) {
    return new Response(JSON.stringify({ error: 'Database credentials not configured in Cloudflare environment' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
    });
  }

  const tursoUrl = rawUrl.replace('libsql://', 'https://');
  const since = new Date(Date.now() - 30 * 86400000).toISOString();

  try {
    const res = await fetch(`${tursoUrl}/v2/pipeline`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        requests: [
          {
            type: 'execute',
            stmt: {
              sql: 'SELECT service_id, service_name, status, latency_ms, status_code, message, timestamp FROM checks WHERE timestamp >= ? ORDER BY timestamp ASC',
              args: [{ type: 'text', value: since }]
            }
          },
          { type: 'close' }
        ]
      })
    });

    if (!res.ok) {
      throw new Error(`Turso HTTP error: ${res.statusText}`);
    }

    const resJson = await res.json();
    const rawRows = resJson.results?.[0]?.response?.result?.rows || [];
    const payload = aggregateChecks(rawRows, 30);

    const response = new Response(JSON.stringify(payload), {
      status: 200,
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'public, max-age=60, s-maxage=60, stale-while-revalidate=120'
      }
    });

    // Store in Cloudflare Edge Cache for 60s
    context.waitUntil(cache.put(cacheKey, response.clone()));
    return response;
  } catch (err) {
    return new Response(JSON.stringify({ error: String(err) }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
    });
  }
}
