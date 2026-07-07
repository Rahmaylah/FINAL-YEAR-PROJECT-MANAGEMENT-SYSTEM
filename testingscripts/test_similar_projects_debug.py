"""
Debug the find_similar_projects() method to see what's happening.

Run with: python test_similar_projects_debug.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fypms.settings')
sys.path.insert(0, '/home/revocajana/projects/fyp')
django.setup()

from projects.models import Project
from projects.similarity import get_similarity_scorer

def main():
    print("\n" + "=" * 80)
    print("DEBUG: find_similar_projects() method")
    print("=" * 80 + "\n")
    
    scorer = get_similarity_scorer()
    
    # Get project 15
    p15 = Project.objects.get(id=15)
    
    print(f"Testing from project: {p15.id} - {p15.title}\n")
    
    # Convert embeddings
    combined_emb = p15.combined_embedding.tolist() if hasattr(p15.combined_embedding, 'tolist') else (list(p15.combined_embedding) if p15.combined_embedding else None)
    
    print(f"Combined embedding length: {len(combined_emb) if combined_emb else 'None'}")
    print(f"First 5 values: {combined_emb[:5] if combined_emb else 'None'}\n")
    
    # Call find_similar_projects
    print("Calling find_similar_projects()...\n")
    similar = scorer.find_similar_projects(
        project_id=p15.id,
        title=p15.title,
        objectives=p15.main_objective,
        title_embedding=combined_emb,  # Using combined for simplicity
        objectives_embedding=combined_emb,
        combined_embedding=combined_emb,
        limit=10
    )
    
    print(f"Found {len(similar)} similar projects:\n")
    
    for i, s in enumerate(similar, 1):
        print(f"{i}. Project {s['id']}: {s['title'][:40]}")
        print(f"   Vector similarity: {s.get('vector_similarity')}")
        print(f"   Hybrid similarity: {s['hybrid_similarity']:.3f}")
        print(f"   Auto-flag: {s['auto_flag']}\n")
    
    # Also manually calculate similarities
    print("=" * 80)
    print("MANUAL SIMILARITY CALCULATIONS")
    print("=" * 80 + "\n")
    
    for p in Project.objects.filter(id__in=[16, 18, 19]):
        p_emb = p.combined_embedding.tolist() if hasattr(p.combined_embedding, 'tolist') else (list(p.combined_embedding) if p.combined_embedding else None)
        
        semantic = scorer.calculate_semantic_similarity(combined_emb, p_emb)
        lexical = scorer.calculate_lexical_similarity(p15.title, p.title)
        hybrid = scorer.calculate_hybrid_similarity(combined_emb, p_emb, p15.title, p.title)
        
        print(f"Project {p.id}:")
        print(f"  Semantic: {semantic:.3f}")
        print(f"  Lexical: {lexical:.3f}")
        print(f"  Hybrid: {hybrid:.3f}\n")

if __name__ == '__main__':
    main()
