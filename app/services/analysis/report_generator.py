"""
Report Generator Service
Generates visual charts and structured reports from analysis results using free methods
"""
import logging
import json
import os
from typing import Dict, Any, List
from datetime import datetime, timezone
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import seaborn as sns
import pandas as pd
import numpy as np
from io import BytesIO
import base64

# Configure logging
logger = logging.getLogger(__name__)

class ReportGenerator:
    """
    Service for generating visual reports and charts from interview analysis results.
    Uses free matplotlib/seaborn - no additional API calls.
    """
    
    def __init__(self):
        """Initialize the report generator."""
        # Set matplotlib style
        plt.style.use('seaborn-v0_8-whitegrid')
        
    def generate_comprehensive_report(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a comprehensive report with visual charts and structured data.
        
        Args:
            analysis_result: Complete analysis result from AnalysisService
            
        Returns:
            Dict containing visual charts and formatted report data
        """
        try:
            logger.info("Generating comprehensive visual report...")
            
            # Extract data from analysis result
            structured_analysis = analysis_result.get("structured_analysis", {})
            scores = structured_analysis.get("scores", {})
            session_metrics = analysis_result.get("session_metrics", {})
            question_responses = analysis_result.get("question_responses", [])
            
            # Generate all charts
            charts = {}
            
            # 1. Skills Assessment Radar Chart
            if scores:
                charts["skills_radar"] = self._create_skills_radar_chart(scores)
                logger.debug("Generated skills radar chart")
            
            # 2. Speaking Patterns Analysis
            if question_responses:
                charts["speaking_analysis"] = self._create_speaking_analysis_chart(question_responses)
                logger.debug("Generated speaking analysis chart")
            
            # 3. Response Quality Analysis
            if question_responses and structured_analysis.get("evidence_examples"):
                charts["response_quality"] = self._create_response_quality_chart(
                    question_responses, structured_analysis.get("evidence_examples", [])
                )
                logger.debug("Generated response quality chart")
            
            # 4. Executive Dashboard
            charts["executive_dashboard"] = self._create_executive_dashboard(
                session_metrics, structured_analysis
            )
            logger.debug("Generated executive dashboard")
            
            # 5. Detailed Performance Breakdown
            charts["performance_breakdown"] = self._create_performance_breakdown(
                structured_analysis, question_responses
            )
            logger.debug("Generated performance breakdown chart")
            
            # Generate structured report summary
            report_summary = self._generate_report_summary(analysis_result)
            
            comprehensive_report = {
                "report_generated_at": datetime.now(timezone.utc).isoformat(),
                "charts": charts,
                "summary": report_summary,
                "charts_count": len(charts),
                "report_version": "1.0"
            }
            
            logger.info(f"Successfully generated comprehensive report with {len(charts)} charts")
            return comprehensive_report
            
        except Exception as e:
            logger.error(f"Error generating comprehensive report: {str(e)}")
            return {
                "error": f"Report generation failed: {str(e)}",
                "charts": {},
                "summary": {"error": "Report generation failed"}
            }

    def _create_skills_radar_chart(self, scores: Dict[str, float]) -> str:
        """Create a professional radar chart for skill scores."""
        try:
            fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
            
            # Prepare data
            categories = list(scores.keys())
            values = list(scores.values())
            
            # Number of variables
            N = len(categories)
            
            # Calculate angles for each axis
            angles = [n / float(N) * 2 * np.pi for n in range(N)]
            angles += angles[:1]  # Complete the circle
            
            # Add values to complete the circle
            values += values[:1]
            
            # Plot the radar chart
            ax.plot(angles, values, 'o-', linewidth=3, label='Candidate Score', color='#2E86AB', markersize=8)
            ax.fill(angles, values, alpha=0.25, color='#2E86AB')
            
            # Add benchmark line (average performance)
            benchmark = [6.0] * len(angles)  # 6/10 as average benchmark
            ax.plot(angles, benchmark, '--', linewidth=2, alpha=0.7, color='#F24236', label='Industry Average')
            
            # Customize the chart
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels([cat.replace('_', ' ').title() for cat in categories], fontsize=12)
            
            # Set y-axis limits and labels
            ax.set_ylim(0, 10)
            ax.set_yticks([2, 4, 6, 8, 10])
            ax.set_yticklabels(['2', '4', '6', '8', '10'], fontsize=10)
            ax.grid(True, alpha=0.3)
            
            # Add title and legend
            plt.title('Skills Assessment Overview', size=16, fontweight='bold', pad=30)
            plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
            
            # Convert to base64
            return self._chart_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Error creating skills radar chart: {str(e)}")
            # Return a simple placeholder chart instead of failing
            fig, ax = plt.subplots(figsize=(8, 6))
            categories = list(scores.keys())
            values = list(scores.values())
            ax.bar(categories, values, color='#2E86AB', alpha=0.7)
            ax.set_title('Skills Assessment (Bar Chart)', fontweight='bold')
            ax.set_ylabel('Score')
            plt.xticks(rotation=45)
            plt.tight_layout()
            return self._chart_to_base64(fig)

    def _create_speaking_analysis_chart(self, question_responses: List[Dict]) -> str:
        """Create comprehensive speaking patterns analysis."""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # Extract data
        questions = [f"Q{i+1}" for i in range(len(question_responses))]
        speaking_rates = [resp.get('speaking_rate', 0) for resp in question_responses]
        durations = [resp.get('duration', 0) for resp in question_responses]
        word_counts = [resp.get('word_count', 0) for resp in question_responses]
        
        # Color palette
        colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D']
        
        # 1. Speaking Rate Analysis
        bars1 = ax1.bar(questions, speaking_rates, color=colors[0], alpha=0.8)
        ax1.set_title('Speaking Rate by Question', fontweight='bold', fontsize=14)
        ax1.set_ylabel('Words per Minute', fontweight='bold')
        ax1.tick_params(axis='x', rotation=45)
        
        # Add average line and optimal range
        avg_rate = np.mean(speaking_rates) if speaking_rates else 0
        ax1.axhline(y=avg_rate, color='red', linestyle='--', alpha=0.7, linewidth=2, label=f'Average: {avg_rate:.1f} wpm')
        ax1.axhspan(120, 160, alpha=0.2, color='green', label='Optimal Range')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for bar, rate in zip(bars1, speaking_rates):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 2,
                    f'{rate:.0f}', ha='center', va='bottom', fontweight='bold')
        
        # 2. Response Duration
        bars2 = ax2.bar(questions, durations, color=colors[1], alpha=0.8)
        ax2.set_title('Response Duration by Question', fontweight='bold', fontsize=14)
        ax2.set_ylabel('Duration (seconds)', fontweight='bold')
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, alpha=0.3)
        
        # Add duration labels
        for bar, duration in zip(bars2, durations):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{duration:.1f}s', ha='center', va='bottom', fontweight='bold')
        
        # 3. Word Count Analysis
        bars3 = ax3.bar(questions, word_counts, color=colors[2], alpha=0.8)
        ax3.set_title('Response Length by Question', fontweight='bold', fontsize=14)
        ax3.set_ylabel('Number of Words', fontweight='bold')
        ax3.tick_params(axis='x', rotation=45)
        ax3.grid(True, alpha=0.3)
        
        # Add word count labels
        for bar, words in zip(bars3, word_counts):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{words}', ha='center', va='bottom', fontweight='bold')
        
        # 4. Speaking Efficiency Trend
        efficiency = [wc/dur if dur > 0 else 0 for wc, dur in zip(word_counts, durations)]
        line = ax4.plot(questions, efficiency, marker='o', linewidth=3, markersize=10, color=colors[3])
        ax4.set_title('Speaking Efficiency Trend', fontweight='bold', fontsize=14)
        ax4.set_ylabel('Words per Second', fontweight='bold')
        ax4.tick_params(axis='x', rotation=45)
        ax4.grid(True, alpha=0.3)
        
        # Add efficiency labels
        for i, (q, eff) in enumerate(zip(questions, efficiency)):
            ax4.annotate(f'{eff:.1f}', (i, eff), textcoords="offset points", 
                        xytext=(0,10), ha='center', fontweight='bold')
        
        plt.suptitle('Communication Patterns Analysis', fontsize=18, fontweight='bold', y=0.98)
        plt.tight_layout()
        
        return self._chart_to_base64(fig)

    def _create_response_quality_chart(self, question_responses: List[Dict], evidence_examples: List[Dict]) -> str:
        """Create response quality and correlation analysis."""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # Extract data
        word_counts = [resp.get('word_count', 0) for resp in question_responses]
        durations = [resp.get('duration', 0) for resp in question_responses]
        speaking_rates = [resp.get('speaking_rate', 0) for resp in question_responses]
        
        # Map evidence examples to quality scores
        quality_scores = []
        for i, resp in enumerate(question_responses):
            evidence_for_question = [e for e in evidence_examples if e.get('question_number') == i + 1]
            if evidence_for_question:
                impact = evidence_for_question[0].get('impact', 'neutral')
                quality_score = {'positive': 8, 'neutral': 5, 'negative': 3}.get(impact, 5)
            else:
                quality_score = 5
            quality_scores.append(quality_score)
        
        # 1. Response Length vs Quality Correlation
        scatter = ax1.scatter(word_counts, quality_scores, s=150, alpha=0.7, 
                             c=quality_scores, cmap='RdYlGn', edgecolors='black', linewidth=1)
        for i, (wc, qs) in enumerate(zip(word_counts, quality_scores)):
            ax1.annotate(f'Q{i+1}', (wc, qs), xytext=(5, 5), textcoords='offset points', 
                        fontsize=10, fontweight='bold')
        
        ax1.set_xlabel('Word Count', fontweight='bold')
        ax1.set_ylabel('Quality Score (1-10)', fontweight='bold')
        ax1.set_title('Response Length vs Quality', fontweight='bold', fontsize=14)
        ax1.grid(True, alpha=0.3)
        plt.colorbar(scatter, ax=ax1, label='Quality Score')
        
        # 2. Question Categories Distribution
        categories = {}
        for resp in question_responses:
            category = resp.get('question_category', 'general')
            categories[category] = categories.get(category, 0) + 1
        
        if categories:
            colors_pie = plt.cm.Set3(np.linspace(0, 1, len(categories)))
            wedges, texts, autotexts = ax2.pie(categories.values(), labels=categories.keys(), 
                                              autopct='%1.1f%%', startangle=90, colors=colors_pie)
            ax2.set_title('Question Categories Distribution', fontweight='bold', fontsize=14)
            
            # Enhance pie chart text
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
        else:
            ax2.text(0.5, 0.5, 'No category data available', ha='center', va='center', 
                    transform=ax2.transAxes, fontsize=12)
            ax2.set_title('Question Categories', fontweight='bold', fontsize=14)
        
        # 3. Speaking Rate vs Quality
        scatter2 = ax3.scatter(speaking_rates, quality_scores, s=150, alpha=0.7,
                              c=durations, cmap='viridis', edgecolors='black', linewidth=1)
        for i, (sr, qs) in enumerate(zip(speaking_rates, quality_scores)):
            ax3.annotate(f'Q{i+1}', (sr, qs), xytext=(5, 5), textcoords='offset points',
                        fontsize=10, fontweight='bold')
        
        ax3.set_xlabel('Speaking Rate (WPM)', fontweight='bold')
        ax3.set_ylabel('Quality Score (1-10)', fontweight='bold')
        ax3.set_title('Speaking Rate vs Quality', fontweight='bold', fontsize=14)
        ax3.grid(True, alpha=0.3)
        plt.colorbar(scatter2, ax=ax3, label='Duration (s)')
        
        # 4. Quality Distribution
        quality_counts = {score: quality_scores.count(score) for score in set(quality_scores)}
        quality_labels = ['Excellent (8+)', 'Good (6-7)', 'Average (4-5)', 'Poor (1-3)']
        quality_values = [
            sum(1 for q in quality_scores if q >= 8),
            sum(1 for q in quality_scores if 6 <= q < 8),
            sum(1 for q in quality_scores if 4 <= q < 6),
            sum(1 for q in quality_scores if q < 4)
        ]
        
        colors_bar = ['#2E8B57', '#32CD32', '#FFD700', '#FF6347']
        bars = ax4.bar(quality_labels, quality_values, color=colors_bar, alpha=0.8)
        ax4.set_title('Quality Score Distribution', fontweight='bold', fontsize=14)
        ax4.set_ylabel('Number of Responses', fontweight='bold')
        ax4.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for bar, value in zip(bars, quality_values):
            if value > 0:
                height = bar.get_height()
                ax4.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                        f'{value}', ha='center', va='bottom', fontweight='bold')
        
        plt.suptitle('Response Quality Analysis', fontsize=18, fontweight='bold', y=0.98)
        plt.tight_layout()
        
        return self._chart_to_base64(fig)

    def _create_executive_dashboard(self, session_metrics: Dict, structured_analysis: Dict) -> str:
        """Create executive summary dashboard."""
        fig = plt.figure(figsize=(16, 12))
        gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)
        
        # 1. Overall Score Gauge (top-left)
        ax1 = fig.add_subplot(gs[0, 0])
        overall_score = structured_analysis.get('overall_score', 0)
        self._create_gauge_chart(ax1, overall_score, 'Overall Score')
        
        # 2. Key Metrics (top-middle-left)
        ax2 = fig.add_subplot(gs[0, 1])
        metrics_text = f"""📊 SESSION METRICS
        
Questions Answered: {session_metrics.get('total_questions', 0)}
Total Words Spoken: {session_metrics.get('total_words', 0):,}
Speaking Duration: {session_metrics.get('total_duration', 0):.1f}s
Average Rate: {session_metrics.get('average_speaking_rate', 0):.1f} wpm
Response Length: {session_metrics.get('average_response_length', 0):.1f} words"""
        
        ax2.text(0.05, 0.95, metrics_text, transform=ax2.transAxes, fontsize=11,
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.5))
        ax2.set_xlim(0, 1)
        ax2.set_ylim(0, 1)
        ax2.axis('off')
        
        # 3. Hiring Recommendation (top-middle-right)
        ax3 = fig.add_subplot(gs[0, 2])
        recommendation = structured_analysis.get('hiring_recommendation', 'requires_review')
        confidence = structured_analysis.get('confidence_level', 'medium')
        
        colors = {'hire': '#28a745', 'no_hire': '#dc3545', 'requires_review': '#ffc107'}
        color = colors.get(recommendation, '#6c757d')
        
        # Create recommendation visualization
        ax3.pie([1], colors=[color], startangle=90, radius=0.8)
        recommendation_text = recommendation.replace("_", " ").title()
        ax3.text(0, 0, f'{recommendation_text}\n\n({confidence.title()} Confidence)', 
                ha='center', va='center', fontsize=12, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
        ax3.set_title('🎯 Hiring Recommendation', fontweight='bold', fontsize=14)
        
        # 4. Skills Breakdown (top-right)
        ax4 = fig.add_subplot(gs[0, 3])
        scores = structured_analysis.get('scores', {})
        if scores:
            skill_names = [name.replace('_', ' ').title() for name in scores.keys()]
            skill_values = list(scores.values())
            
            bars = ax4.barh(skill_names, skill_values, color=plt.cm.RdYlGn(np.array(skill_values)/10))
            ax4.set_xlim(0, 10)
            ax4.set_xlabel('Score (1-10)', fontweight='bold')
            ax4.set_title('🔧 Skills Breakdown', fontweight='bold', fontsize=14)
            
            # Add score labels
            for i, (bar, score) in enumerate(zip(bars, skill_values)):
                ax4.text(score + 0.1, bar.get_y() + bar.get_height()/2,
                        f'{score:.1f}', va='center', fontweight='bold')
        
        # 5. Strengths vs Weaknesses (middle row)
        ax5 = fig.add_subplot(gs[1, :])
        assessment = structured_analysis.get('assessment', {})
        strengths = assessment.get('strengths', [])
        weaknesses = assessment.get('weaknesses', [])
        
        max_items = max(len(strengths), len(weaknesses), 1)
        y_pos = np.arange(max_items)
        
        # Create horizontal bar chart
        if strengths:
            ax5.barh(y_pos[:len(strengths)], [1] * len(strengths), 
                    left=0, color='#28a745', alpha=0.7, label=f'✅ Strengths ({len(strengths)})')
        if weaknesses:
            ax5.barh(y_pos[:len(weaknesses)], [-1] * len(weaknesses), 
                    left=0, color='#dc3545', alpha=0.7, label=f'⚠️ Areas for Improvement ({len(weaknesses)})')
        
        # Add text labels
        for i, strength in enumerate(strengths):
            if i < max_items:
                text = strength[:60] + ('...' if len(strength) > 60 else '')
                ax5.text(0.02, i, text, ha='left', va='center', fontsize=10, fontweight='bold')
        
        for i, weakness in enumerate(weaknesses):
            if i < max_items:
                text = weakness[:60] + ('...' if len(weakness) > 60 else '')
                ax5.text(-0.02, i, text, ha='right', va='center', fontsize=10, fontweight='bold')
        
        ax5.set_xlim(-1.2, 1.2)
        ax5.set_ylim(-0.5, max_items - 0.5)
        ax5.set_yticks([])
        ax5.axvline(x=0, color='black', linewidth=1)
        ax5.set_title('💪 Strengths vs Areas for Improvement', fontweight='bold', fontsize=16)
        ax5.legend(loc='upper right')
        
        # 6. Key Insights (bottom row)
        ax6 = fig.add_subplot(gs[2, :2])
        insights = structured_analysis.get('key_insights', [])
        insights_text = "🔍 KEY INSIGHTS:\n\n"
        for i, insight in enumerate(insights[:4], 1):  # Show top 4 insights
            insights_text += f"{i}. {insight}\n\n"
        
        ax6.text(0.05, 0.95, insights_text, transform=ax6.transAxes, fontsize=11,
                verticalalignment='top', wrap=True,
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow", alpha=0.7))
        ax6.set_xlim(0, 1)
        ax6.set_ylim(0, 1)
        ax6.axis('off')
        
        # 7. Follow-up Actions (bottom-right)
        ax7 = fig.add_subplot(gs[2, 2:])
        follow_ups = structured_analysis.get('follow_up_questions', [])
        recommendations = structured_analysis.get('recommendations', {})
        next_steps = recommendations.get('next_steps', 'No specific recommendations provided')
        
        actions_text = f"📋 NEXT STEPS:\n\n{next_steps}\n\n"
        if follow_ups:
            actions_text += "❓ FOLLOW-UP QUESTIONS:\n"
            for i, question in enumerate(follow_ups[:3], 1):
                actions_text += f"{i}. {question}\n"
        
        ax7.text(0.05, 0.95, actions_text, transform=ax7.transAxes, fontsize=11,
                verticalalignment='top', wrap=True,
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgreen", alpha=0.7))
        ax7.set_xlim(0, 1)
        ax7.set_ylim(0, 1)
        ax7.axis('off')
        
        plt.suptitle('📈 Executive Interview Summary Dashboard', fontsize=20, fontweight='bold', y=0.98)
        
        return self._chart_to_base64(fig)

    def _create_performance_breakdown(self, structured_analysis: Dict, question_responses: List[Dict]) -> str:
        """Create detailed performance breakdown chart."""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. Question-by-Question Performance
        evidence_examples = structured_analysis.get('evidence_examples', [])
        question_scores = []
        for i in range(len(question_responses)):
            evidence_for_q = [e for e in evidence_examples if e.get('question_number') == i + 1]
            if evidence_for_q:
                impact = evidence_for_q[0].get('impact', 'neutral')
                score = {'positive': 8, 'neutral': 5, 'negative': 3}.get(impact, 5)
            else:
                score = 5
            question_scores.append(score)
        
        questions = [f"Q{i+1}" for i in range(len(question_responses))]
        colors = ['#28a745' if s >= 7 else '#ffc107' if s >= 5 else '#dc3545' for s in question_scores]
        
        bars = ax1.bar(questions, question_scores, color=colors, alpha=0.8)
        ax1.set_title('Question-by-Question Performance', fontweight='bold', fontsize=14)
        ax1.set_ylabel('Performance Score', fontweight='bold')
        ax1.set_ylim(0, 10)
        ax1.grid(True, alpha=0.3)
        
        # Add score labels
        for bar, score in zip(bars, question_scores):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{score}', ha='center', va='bottom', fontweight='bold')
        
        # 2. Assessment Quality Breakdown
        assessment = structured_analysis.get('assessment', {})
        quality_metrics = {
            'Communication': assessment.get('communication_quality', 'fair'),
            'Response Depth': assessment.get('response_depth', 'fair'),
            'Technical Accuracy': assessment.get('technical_accuracy', 'fair')
        }
        
        quality_scores = {
            'excellent': 9, 'good': 7, 'fair': 5, 'poor': 3
        }
        
        metrics = list(quality_metrics.keys())
        values = [quality_scores.get(quality_metrics[m], 5) for m in metrics]
        colors_quality = ['#28a745' if v >= 7 else '#ffc107' if v >= 5 else '#dc3545' for v in values]
        
        bars2 = ax2.bar(metrics, values, color=colors_quality, alpha=0.8)
        ax2.set_title('Assessment Quality Breakdown', fontweight='bold', fontsize=14)
        ax2.set_ylabel('Quality Score', fontweight='bold')
        ax2.set_ylim(0, 10)
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, alpha=0.3)
        
        # Add quality labels
        for bar, score, metric in zip(bars2, values, metrics):
            height = bar.get_height()
            quality_text = list(quality_metrics.values())[list(quality_metrics.keys()).index(metric)]
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{score}\n({quality_text})', ha='center', va='bottom', 
                    fontweight='bold', fontsize=9)
        
        # 3. Skills Heat Map
        scores = structured_analysis.get('scores', {})
        if scores:
            skills_data = []
            for skill, score in scores.items():
                skills_data.append([skill.replace('_', ' ').title(), 'Candidate', score])
                skills_data.append([skill.replace('_', ' ').title(), 'Benchmark', 6.0])  # Industry average
            
            df = pd.DataFrame(skills_data, columns=['Skill', 'Type', 'Score'])
            pivot_df = df.pivot(index='Skill', columns='Type', values='Score')
            
            sns.heatmap(pivot_df, annot=True, cmap='RdYlGn', center=5, 
                       vmin=0, vmax=10, ax=ax3, cbar_kws={'label': 'Score'})
            ax3.set_title('Skills vs Benchmark Comparison', fontweight='bold', fontsize=14)
            ax3.set_xlabel('')
            ax3.set_ylabel('')
        
        # 4. Confidence and Recommendation Summary
        confidence_level = structured_analysis.get('confidence_level', 'medium')
        hiring_rec = structured_analysis.get('hiring_recommendation', 'requires_review')
        overall_score = structured_analysis.get('overall_score', 0)
        
        # Create summary metrics
        summary_data = {
            'Overall Score': overall_score,
            'Confidence': {'high': 9, 'medium': 6, 'low': 3}.get(confidence_level, 6),
            'Recommendation': {'hire': 9, 'requires_review': 6, 'no_hire': 3}.get(hiring_rec, 6)
        }
        
        metrics_names = list(summary_data.keys())
        metrics_values = list(summary_data.values())
        colors_summary = ['#28a745' if v >= 7 else '#ffc107' if v >= 5 else '#dc3545' for v in metrics_values]
        
        bars4 = ax4.bar(metrics_names, metrics_values, color=colors_summary, alpha=0.8)
        ax4.set_title('Summary Assessment Metrics', fontweight='bold', fontsize=14)
        ax4.set_ylabel('Score/Level', fontweight='bold')
        ax4.set_ylim(0, 10)
        ax4.grid(True, alpha=0.3)
        
        # Add value labels
        labels = [f'{overall_score:.1f}', confidence_level.title(), hiring_rec.replace('_', ' ').title()]
        for bar, value, label in zip(bars4, metrics_values, labels):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{value:.1f}\n({label})', ha='center', va='bottom', 
                    fontweight='bold', fontsize=10)
        
        plt.suptitle('Detailed Performance Analysis', fontsize=18, fontweight='bold', y=0.98)
        plt.tight_layout()
        
        return self._chart_to_base64(fig)

    def _create_gauge_chart(self, ax, value: float, title: str):
        """Create a professional gauge chart for scores."""
        # Create gauge sectors
        theta = np.linspace(0, np.pi, 100)
        
        # Define score ranges and colors
        ranges = [(0, 3, '#dc3545'), (3, 5, '#ffc107'), (5, 7, '#17a2b8'), (7, 8.5, '#28a745'), (8.5, 10, '#20c997')]
        
        for start, end, color in ranges:
            start_angle = (start / 10) * np.pi
            end_angle = (end / 10) * np.pi
            theta_section = np.linspace(start_angle, end_angle, 20)
            ax.fill_between(theta_section, 0, 1, alpha=0.7, color=color)
        
        # Add score needle
        score_angle = (value / 10) * np.pi
        ax.plot([score_angle, score_angle], [0, 0.8], 'k-', linewidth=4)
        ax.plot(score_angle, 0.8, 'ko', markersize=10)
        
        # Add score text
        ax.text(np.pi/2, 0.5, f'{value:.1f}', ha='center', va='center', 
                fontsize=20, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
        
        # Formatting
        ax.set_ylim(0, 1)
        ax.set_xlim(0, np.pi)
        ax.set_theta_zero_location('W')
        ax.set_thetagrids([0, 36, 72, 108, 144, 180], ['0', '2', '4', '6', '8', '10'])
        ax.set_yticks([])
        ax.set_title(title, fontweight='bold', fontsize=14, pad=20)

    def _generate_report_summary(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a structured summary of the analysis report."""
        structured_analysis = analysis_result.get("structured_analysis", {})
        session_metrics = analysis_result.get("session_metrics", {})
        
        return {
            "candidate_id": analysis_result.get("candidate_id"),
            "session_id": analysis_result.get("session_id"),
            "overall_assessment": {
                "score": structured_analysis.get("overall_score", 0),
                "recommendation": structured_analysis.get("hiring_recommendation", "requires_review"),
                "confidence": structured_analysis.get("confidence_level", "medium")
            },
            "key_metrics": {
                "total_questions": session_metrics.get("total_questions", 0),
                "total_words": session_metrics.get("total_words", 0),
                "average_speaking_rate": session_metrics.get("average_speaking_rate", 0),
                "total_duration": session_metrics.get("total_duration", 0)
            },
            "skills_summary": structured_analysis.get("scores", {}),
            "top_strengths": structured_analysis.get("assessment", {}).get("strengths", [])[:3],
            "key_concerns": structured_analysis.get("assessment", {}).get("weaknesses", [])[:3],
            "next_steps": structured_analysis.get("recommendations", {}).get("next_steps", ""),
            "analysis_quality": {
                "communication": structured_analysis.get("assessment", {}).get("communication_quality", "fair"),
                "response_depth": structured_analysis.get("assessment", {}).get("response_depth", "fair"),
                "technical_accuracy": structured_analysis.get("assessment", {}).get("technical_accuracy", "fair")
            }
        }

    def _chart_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 string."""
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        chart_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close(fig)
        return chart_base64


# Create singleton instance
report_generator = ReportGenerator()
