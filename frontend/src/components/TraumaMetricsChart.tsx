import React from 'react';
import { TrendingUp, Activity, Sparkles } from 'lucide-react';
import {
  BarChart,
  Bar,
  Cell,
  CartesianGrid,
  LabelList,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

export interface TraumaIndicatorData {
  indicator: string;
  score: number;
  category: string;
  color: string;
}

interface TraumaMetricsChartProps {
  callerId: string;
  callerNumber: string;
  riskLevel: 'CRITICAL' | 'HIGH' | 'LOW';
  sviScore: number;
  data: TraumaIndicatorData[];
}

export const TraumaMetricsChart: React.FC<TraumaMetricsChartProps> = ({
  callerNumber,
  riskLevel,
  sviScore,
  data,
}) => {
  // Compute key summary stats for visual appeal
  const maxItem = data.length > 0 
    ? [...data].sort((a, b) => b.score - a.score)[0] 
    : { indicator: 'None', score: 0, category: 'N/A', color: '#64748b' };

  const avgDistress = data.length > 0
    ? Math.round(data.reduce((sum, d) => sum + d.score, 0) / data.length)
    : 0;

  const criticalCount = data.filter((d) => d.score >= 75).length;

  return (
    <div
      style={{
        backgroundColor: '#ffffff',
        border: '1px solid #e2e8f0',
        borderRadius: '16px',
        padding: '24px',
        marginBottom: '24px',
        boxShadow: '0 4px 20px -2px rgba(15, 23, 42, 0.05)',
        position: 'relative',
        overflow: 'hidden'
      }}
    >
      {/* Decorative subtle ambient glow top-right */}
      <div
        style={{
          position: 'absolute',
          top: -40,
          right: -40,
          width: '160px',
          height: '160px',
          borderRadius: '50%',
          background: riskLevel === 'CRITICAL' 
            ? 'radial-gradient(circle, rgba(239, 68, 68, 0.12) 0%, rgba(255, 255, 255, 0) 70%)'
            : 'radial-gradient(circle, rgba(245, 158, 11, 0.12) 0%, rgba(255, 255, 255, 0) 70%)',
          pointerEvents: 'none'
        }}
      />

      {/* Header section */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '14px', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '26px',
                height: '26px',
                borderRadius: '8px',
                backgroundColor: riskLevel === 'CRITICAL' ? '#fee2e2' : '#fef3c7',
                color: riskLevel === 'CRITICAL' ? '#dc2626' : '#d97706'
              }}
            >
              <Activity style={{ width: '15px', height: '15px' }} />
            </span>
            <h4
              style={{
                fontSize: '17px',
                fontWeight: 800,
                margin: 0,
                color: '#0f172a',
                letterSpacing: '-0.02em',
              }}
            >
              PS 26093 Trauma &amp; Distress Indicators
            </h4>
          </div>
          <p style={{ fontSize: '13px', color: '#64748b', margin: 0, lineHeight: 1.4 }}>
            Multi-modal biometric acoustic prosody, linguistic coercion &amp; threat telemetry for <span style={{ fontWeight: 600, color: '#1e293b' }}>{callerNumber}</span>
          </p>
        </div>

        {/* Live status badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '9999px',
              fontSize: '12px',
              fontWeight: 700,
              letterSpacing: '0.04em',
              backgroundColor: riskLevel === 'CRITICAL' ? '#fef2f2' : '#fffbeb',
              color: riskLevel === 'CRITICAL' ? '#991b1b' : '#92400e',
              border: `1px solid ${riskLevel === 'CRITICAL' ? '#fecaca' : '#fde68a'}`,
              boxShadow: '0 1px 2px rgba(0,0,0,0.04)'
            }}
          >
            <span
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                backgroundColor: riskLevel === 'CRITICAL' ? '#dc2626' : '#f59e0b',
                boxShadow: riskLevel === 'CRITICAL' ? '0 0 8px #dc2626' : '0 0 8px #f59e0b'
              }}
            />
            SVI {(sviScore * 100).toFixed(0)}% • {riskLevel}
          </div>
        </div>
      </div>

      {/* Mini Telemetry KPI Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '12px',
          marginBottom: '20px'
        }}
      >
        <div
          style={{
            backgroundColor: '#f8fafc',
            border: '1px solid #edf2f7',
            borderRadius: '10px',
            padding: '12px 14px'
          }}
        >
          <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#64748b', marginBottom: '4px' }}>
            Primary Distress Vector
          </div>
          <div style={{ fontSize: '13.5px', fontWeight: 700, color: '#0f172a', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {maxItem.indicator}
          </div>
          <div style={{ fontSize: '11.5px', color: maxItem.color, fontWeight: 700, marginTop: '2px' }}>
            {maxItem.score}% Peak Intensity
          </div>
        </div>

        <div
          style={{
            backgroundColor: '#f8fafc',
            border: '1px solid #edf2f7',
            borderRadius: '10px',
            padding: '12px 14px'
          }}
        >
          <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#64748b', marginBottom: '4px' }}>
            Average Trauma Load
          </div>
          <div style={{ fontSize: '13.5px', fontWeight: 700, color: '#0f172a' }}>
            {avgDistress}% SVI Composite
          </div>
          <div style={{ fontSize: '11.5px', color: avgDistress >= 60 ? '#dc2626' : '#059669', fontWeight: 600, marginTop: '2px' }}>
            {avgDistress >= 60 ? '⚡ High Burden Triage' : '✓ Manageable Level'}
          </div>
        </div>

        <div
          style={{
            backgroundColor: '#f8fafc',
            border: '1px solid #edf2f7',
            borderRadius: '10px',
            padding: '12px 14px'
          }}
        >
          <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#64748b', marginBottom: '4px' }}>
            Critical Flag Triggers
          </div>
          <div style={{ fontSize: '13.5px', fontWeight: 700, color: '#0f172a' }}>
            {criticalCount} of 8 Indicators &gt; 75%
          </div>
          <div style={{ fontSize: '11.5px', color: criticalCount > 0 ? '#b91c1c' : '#64748b', fontWeight: 600, marginTop: '2px' }}>
            {criticalCount > 0 ? '🚨 Statutory Escalation Active' : 'Normal Standby'}
          </div>
        </div>
      </div>

      {/* Modern Gradient Bar Chart with Track Background */}
      <div style={{ width: '100%', height: 350 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{
              top: 8,
              right: 60,
              bottom: 8,
              left: 10,
            }}
            barCategoryGap={10}
          >
            {/* SVG Linear Gradients for Visually Appealing Bar Fills */}
            <defs>
              <linearGradient id="bar-grad-0" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#f43f5e" />
                <stop offset="100%" stopColor="#b91c1c" />
              </linearGradient>
              <linearGradient id="bar-grad-1" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#fb7185" />
                <stop offset="100%" stopColor="#e11d48" />
              </linearGradient>
              <linearGradient id="bar-grad-2" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#f87171" />
                <stop offset="100%" stopColor="#991b1b" />
              </linearGradient>
              <linearGradient id="bar-grad-3" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#fbbf24" />
                <stop offset="100%" stopColor="#ea580c" />
              </linearGradient>
              <linearGradient id="bar-grad-4" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#c084fc" />
                <stop offset="100%" stopColor="#7c3aed" />
              </linearGradient>
              <linearGradient id="bar-grad-5" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#60a5fa" />
                <stop offset="100%" stopColor="#2563eb" />
              </linearGradient>
              <linearGradient id="bar-grad-6" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#fcd34d" />
                <stop offset="100%" stopColor="#d97706" />
              </linearGradient>
              <linearGradient id="bar-grad-7" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#94a3b8" />
                <stop offset="100%" stopColor="#475569" />
              </linearGradient>
            </defs>

            <CartesianGrid horizontal={false} stroke="#f1f5f9" strokeDasharray="3 3" />
            <YAxis
              dataKey="indicator"
              type="category"
              tickLine={false}
              axisLine={false}
              width={150}
              tick={{ fill: '#334155', fontSize: 12.5, fontWeight: 600 }}
            />
            <XAxis dataKey="score" type="number" domain={[0, 100]} hide />
            <Tooltip
              cursor={{ fill: 'rgba(241, 245, 249, 0.6)' }}
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const item = payload[0].payload as TraumaIndicatorData;
                  return (
                    <div
                      style={{
                        backgroundColor: 'rgba(15, 23, 42, 0.95)',
                        backdropFilter: 'blur(8px)',
                        color: '#ffffff',
                        padding: '12px 16px',
                        borderRadius: '10px',
                        fontSize: '12.5px',
                        boxShadow: '0 10px 25px -3px rgba(0, 0, 0, 0.3)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        minWidth: '200px'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 700, fontSize: '13.5px', marginBottom: '2px' }}>
                        <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: item.color }} />
                        {item.indicator}
                      </div>
                      <div style={{ color: '#94a3b8', fontSize: '11.5px', marginBottom: '8px' }}>
                        {item.category}
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <span style={{ color: '#cbd5e1', fontSize: '12px' }}>Distress Rating</span>
                        <span style={{ color: item.color, fontWeight: 800, fontSize: '15px' }}>{item.score}%</span>
                      </div>
                      {/* Mini visual gauge inside tooltip */}
                      <div style={{ width: '100%', height: '5px', backgroundColor: 'rgba(255, 255, 255, 0.15)', borderRadius: '3px', overflow: 'hidden' }}>
                        <div style={{ width: `${item.score}%`, height: '100%', backgroundColor: item.color, borderRadius: '3px' }} />
                      </div>
                      <div style={{ marginTop: '8px', fontSize: '11px', color: item.score >= 75 ? '#f87171' : item.score >= 50 ? '#fbbf24' : '#34d399', fontWeight: 600 }}>
                        {item.score >= 75 ? '⚡ CRITICAL INTERVENTION THRESHOLD' : item.score >= 50 ? '● ELEVATED MONITORING' : '✓ BASELINE SAFE'}
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar
              dataKey="score"
              background={{ fill: '#f8fafc' }}
              radius={[0, 8, 8, 0]}
              barSize={18}
              isAnimationActive={true}
              animationDuration={600}
            >
              {data.map((_, index) => (
                <Cell key={`cell-${index}`} fill={`url(#bar-grad-${index % 8})`} />
              ))}
              <LabelList
                dataKey="score"
                position="right"
                offset={12}
                fill="#0f172a"
                fontSize={12}
                fontWeight={700}
                formatter={(val: unknown) => `${val}%`}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Sleek Insight Footer */}
      <div
        style={{
          borderTop: '1px solid #f1f5f9',
          paddingTop: '14px',
          marginTop: '10px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '10px',
          fontSize: '12.5px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#334155', fontWeight: 600 }}>
          <TrendingUp style={{ width: '15px', height: '15px', color: '#dc2626' }} />
          <span>Real-Time Biometric Analysis: Calibrated for Eastern Indian Dialects (Odia, Desia, Kosli, Kuvi)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#64748b' }}>
          <Sparkles style={{ width: '14px', height: '14px', color: '#8b5cf6' }} />
          <span>Section 15A SC/ST PoA Protection Standard Compliant</span>
        </div>
      </div>
    </div>
  );
};
