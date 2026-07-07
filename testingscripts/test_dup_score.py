"""
Test script to debug duplicate detection and similarity scoring.

Run with: python test_dup_score.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fypms.settings')
sys.path.insert(0, '/home/revocajana/projects/fyp')
django.setup()

from projects.models import Project, DuplicateFlag
from projects.similarity import get_similarity_scorer

def print_header(text):
    print("\n" + "=" * 80)
    print(text.center(80))
    print("=" * 80 + "\n")

def print_section(text):
    print("\n" + "-" * 80)
    print(text)
    print("-" * 80)

def main():
    scorer = get_similarity_scorer()
    
    print_header("DUPLICATE DETECTION DEBUG SCRIPT")
    
    # Get all projects
    projects = Project.objects.all().order_by('-created_at')
    
    print(f"Total projects in database: {projects.count()}\n")
    
    # Show configuration
    print_section("SIMILARITY SCORER CONFIGURATION")
    print(f"Semantic weight:       {scorer.semantic_weight}")
    print(f"Lexical weight:        {scorer.lexical_weight}")
    print(f"Similarity threshold:  {scorer.similarity_threshold}")
    print(f"Auto-flag threshold:   {scorer.auto_flag_threshold}")
    print(f"Embedding model:       {scorer.embedding_service.model_name}")
    
    # Show all projects and their embedding status
    print_section("ALL PROJECTS")
    for i, p in enumerate(projects, 1):
        has_emb = "✓" if p.combined_embedding is not None else "✗"
        score = f"{p.duplicate_check_score:.3f}" if p.duplicate_check_score else "None"
        flagged = "🚩" if p.is_flagged_duplicate else " "
        print(f"{i}. [{has_emb}] ID {p.id}: {p.title}")
        print(f"   Score: {score} {flagged}\n")
    
    # Check duplicate flags
    print_section("DUPLICATE FLAGS")
    flags = DuplicateFlag.objects.all().order_by('-similarity_score')
    if flags.exists():
        print(f"Total flags: {flags.count()}\n")
        for i, flag in enumerate(flags[:10], 1):
            print(f"{i}. {flag.project.title} ↔ {flag.similar_project.title}")
            print(f"   Score: {flag.similarity_score:.3f} (Reviewed: {flag.reviewed})\n")
    else:
        print("⚠️  No duplicate flags found!\n")
    
    # Compare all project pairs
    print_section("DETAILED PAIRWISE SIMILARITY ANALYSIS")
    project_list = list(projects)
    
    if len(project_list) < 2:
        print("Not enough projects to compare (need at least 2)\n")
        return
    
    all_scores = []
    
    for i in range(len(project_list)):
        for j in range(i + 1, len(project_list)):
            p1 = project_list[i]
            p2 = project_list[j]
            
            # Check if both have embeddings
            if p1.combined_embedding is None or p2.combined_embedding is None:
                print(f"SKIP: {p1.title[:40]} ↔ {p2.title[:40]}")
                print(f"      Missing embeddings: P1={p1.combined_embedding is not None}, P2={p2.combined_embedding is not None}\n")
                continue
            
            # Calculate scores
            try:
                # Convert numpy arrays to lists for scoring
                emb1 = p1.combined_embedding.tolist() if hasattr(p1.combined_embedding, 'tolist') else list(p1.combined_embedding)
                emb2 = p2.combined_embedding.tolist() if hasattr(p2.combined_embedding, 'tolist') else list(p2.combined_embedding)
                
                semantic_score = scorer.calculate_semantic_similarity(emb1, emb2)
                lexical_score = scorer.calculate_lexical_similarity(
                    f"{p1.title} {p1.main_objective}",
                    f"{p2.title} {p2.main_objective}"
                )
                hybrid_score = scorer.calculate_hybrid_similarity(
                    emb1,
                    emb2,
                    p1.title,
                    p2.title
                )
                
                all_scores.append({
                    'p1': p1,
                    'p2': p2,
                    'semantic': semantic_score,
                    'lexical': lexical_score,
                    'hybrid': hybrid_score
                })
                
                # Color coding
                if hybrid_score >= scorer.auto_flag_threshold:
                    indicator = "🔴 AUTO-FLAG"
                elif hybrid_score >= scorer.similarity_threshold:
                    indicator = "🟡 THRESHOLD"
                else:
                    indicator = "🟢 OK"
                
                print(f"{indicator}: {p1.title[:35]} ↔ {p2.title[:35]}")
                print(f"         Semantic: {semantic_score:.3f} | Lexical: {lexical_score:.3f} | Hybrid: {hybrid_score:.3f}\n")
                
            except Exception as e:
                print(f"ERROR comparing {p1.id} and {p2.id}: {e}\n")
    
    # Summary
    print_section("SUMMARY")
    print(f"Total comparisons made: {len(all_scores)}")
    
    auto_flag_count = sum(1 for s in all_scores if s['hybrid'] >= scorer.auto_flag_threshold)
    threshold_count = sum(1 for s in all_scores if s['hybrid'] >= scorer.similarity_threshold)
    
    print(f"Projects that should be auto-flagged (≥{scorer.auto_flag_threshold}): {auto_flag_count}")
    print(f"Projects above threshold (≥{scorer.similarity_threshold}): {threshold_count}")
    
    if all_scores:
        highest = max(all_scores, key=lambda x: x['hybrid'])
        print(f"\nHighest similarity found:")
        print(f"  {highest['p1'].title} ↔ {highest['p2'].title}")
        print(f"  Score: {highest['hybrid']:.3f}")
    
    print()

if __name__ == '__main__':
    main()
