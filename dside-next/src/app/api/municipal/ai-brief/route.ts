import { NextRequest, NextResponse } from 'next/server';
import { createServiceClient } from '@/lib/supabase';
import Anthropic from '@anthropic-ai/sdk';
import { formatNumber, formatCurrency, formatPercent, PROFILE_CONFIG } from '@/lib/utils';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { mun_code } = body;

    if (!mun_code || typeof mun_code !== 'string') {
      return NextResponse.json(
        { error: 'mun_code is required and must be a string.' },
        { status: 400 }
      );
    }

    const supabase = createServiceClient();

    // Fetch municipality data
    const { data: municipality, error: munError } = await supabase
      .from('municipalities')
      .select('*')
      .eq('mun_code', mun_code)
      .single();

    if (munError || !municipality) {
      return NextResponse.json(
        { error: `Municipality not found: ${mun_code}` },
        { status: 404 }
      );
    }

    // Fetch profile
    const { data: profile } = await supabase
      .from('municipal_profiles')
      .select('*')
      .eq('mun_code', mun_code)
      .order('year', { ascending: false })
      .limit(1)
      .single();

    // Fetch latest unemployment data
    const { data: unemployment } = await supabase
      .from('unemployment_data')
      .select('*')
      .eq('mun_code', mun_code)
      .order('year', { ascending: false })
      .order('quarter', { ascending: false })
      .limit(1)
      .single();

    // Fetch finance data
    const { data: finance } = await supabase
      .from('municipal_finances')
      .select('*')
      .eq('mun_code', mun_code)
      .order('financial_year', { ascending: false })
      .limit(2);

    // Fetch skills gaps for the province
    const { data: skillsGaps } = await supabase
      .from('skills_gaps')
      .select('*')
      .eq('province', municipality.province)
      .order('gap', { ascending: false })
      .limit(5);

    // Build context for Claude
    const profileLabel = profile
      ? PROFILE_CONFIG[profile.profile]?.label || `Profile ${profile.profile}`
      : 'Unknown';

    const contextParts: string[] = [
      `Municipality: ${municipality.mun_name} (Code: ${mun_code})`,
      `Province: ${municipality.province}, District: ${municipality.district}`,
      `Population: ${formatNumber(municipality.population)}, Youth Population: ${formatNumber(municipality.youth_population)}`,
    ];

    if (profile) {
      contextParts.push(
        `\nPerformance Profile: ${profileLabel}`,
        `Welfare Measure: ${profile.welfare_measure.toFixed(1)}%`,
        `Efficiency Measure: ${profile.efficiency_measure.toFixed(1)}%`,
        `Opportunity Measure: ${profile.opportunity_measure.toFixed(1)}%`,
        `Service Delivery Score: ${profile.service_delivery_score.toFixed(1)}%`
      );
    }

    if (unemployment) {
      contextParts.push(
        `\nLatest Unemployment Data (${unemployment.year} Q${unemployment.quarter}):`,
        `Overall Unemployment Rate: ${unemployment.unemployment_rate.toFixed(1)}%`,
        `Youth Unemployment Rate: ${unemployment.youth_unemployment_rate.toFixed(1)}%`,
        `NEET Rate: ${unemployment.neet_rate.toFixed(1)}%`,
        `Absorption Rate: ${unemployment.absorption_rate.toFixed(1)}%`
      );
    }

    if (finance && finance.length > 0) {
      const latest = finance[0];
      contextParts.push(
        `\nFinancial Data (FY${latest.financial_year}):`,
        `Total Revenue: ${formatCurrency(latest.total_revenue)}`,
        `Total Expenditure: ${formatCurrency(latest.total_expenditure)}`,
        `Capital Expenditure: ${formatCurrency(latest.capital_expenditure)}`,
        `Operating Expenditure: ${formatCurrency(latest.operating_expenditure)}`,
        `Service Delivery Spend: ${formatCurrency(latest.service_delivery_spend)}`,
        `Audit Outcome: ${latest.audit_outcome}`
      );

      if (finance.length > 1) {
        const previous = finance[1];
        const revenueChange =
          ((latest.total_revenue - previous.total_revenue) / previous.total_revenue) * 100;
        const expenditureChange =
          ((latest.total_expenditure - previous.total_expenditure) / previous.total_expenditure) *
          100;
        contextParts.push(
          `\nYear-over-year change:`,
          `Revenue change: ${revenueChange > 0 ? '+' : ''}${revenueChange.toFixed(1)}%`,
          `Expenditure change: ${expenditureChange > 0 ? '+' : ''}${expenditureChange.toFixed(1)}%`
        );
      }
    }

    if (skillsGaps && skillsGaps.length > 0) {
      contextParts.push(`\nTop Skills Gaps in ${municipality.province}:`);
      skillsGaps.forEach((sg: Record<string, unknown>) => {
        contextParts.push(
          `- ${sg.occupation} (${sg.sector}): demand ${sg.demand_count}, supply ${sg.supply_count}, gap ${sg.gap}`
        );
      });
    }

    const context = contextParts.join('\n');

    // Call Claude API
    const anthropic = new Anthropic({
      apiKey: process.env.ANTHROPIC_API_KEY!,
    });

    const message = await anthropic.messages.create({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 1024,
      messages: [
        {
          role: 'user',
          content: `You are an expert analyst for South African municipal governance and service delivery. Based on the following data, generate a 3-paragraph executive summary of this municipality's performance.

Paragraph 1: Overall assessment - classify the municipality's health and key headline numbers.
Paragraph 2: Key strengths and weaknesses - be specific about which scores are above or below benchmarks.
Paragraph 3: Recommended actions - concrete, actionable recommendations based on the data.

Use plain language suitable for municipal officials and NGO partners. Be specific about numbers. Do not use bullet points - write flowing prose.

Data:
${context}`,
        },
      ],
    });

    const brief =
      message.content[0].type === 'text'
        ? message.content[0].text
        : 'Unable to generate analysis.';

    return NextResponse.json({ brief });
  } catch (err) {
    console.error('AI brief error:', err);
    return NextResponse.json(
      { error: 'Failed to generate AI analysis. Please try again later.' },
      { status: 500 }
    );
  }
}
