import difflib
import hashlib
import re
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import json
from datetime import datetime

try:
    from fuzzywuzzy import fuzz, process
    import spacy
    from sentence_transformers import SentenceTransformer, util
    import pandas as pd
    import numpy as np
except ImportError:
    print("⚠️ Some features require additional packages. Run:")
    print("pip install fuzzywuzzy python-Levenshtein spacy sentence-transformers pandas")
    print("python -m spacy download en_core_web_md")

PLAGIARISM_CONFIG = {
    "similarity_threshold": 0.75,
    "high_similarity": 0.90,
    "min_sentence_length": 10,
    "n_gram_size": 3,
    "database_path": "./plagiarism_db/",
    "report_path": "./reports/",
    "cache_results": True,
    "use_semantic": True,
    "use_fuzzy": True,
    "check_citations": True
}

class PlagiarismChecker:
    
    def __init__(self, config: Dict = None):
        self.config = config or PLAGIARISM_CONFIG
        self.results_cache = {}
        self.nlp = None
        self.sentence_model = None
        
        os.makedirs(self.config["database_path"], exist_ok=True)
        os.makedirs(self.config["report_path"], exist_ok=True)
        
        if self.config["use_semantic"]:
            try:
                self.nlp = spacy.load("en_core_web_md")
                self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
                print("✅ Semantic models loaded successfully")
            except:
                print("⚠️ Semantic models not available. Run: python -m spacy download en_core_web_md")
    
    def preprocess_text(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def tokenize_sentences(self, text: str) -> List[str]:
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 0]
    
    def generate_ngrams(self, text: str, n: int = 3) -> List[str]:
        words = text.split()
        ngrams = []
        
        for i in range(len(words) - n + 1):
            ngram = ' '.join(words[i:i+n])
            ngrams.append(ngram)
        
        return ngrams
    
    def check_similarity_difflib(self, text1: str, text2: str) -> float:
        text1_clean = self.preprocess_text(text1)
        text2_clean = self.preprocess_text(text2)
        
        similarity = difflib.SequenceMatcher(None, text1_clean, text2_clean).ratio()
        return similarity
    
    def check_similarity_fuzzy(self, text1: str, text2: str) -> Dict[str, float]:
        text1_clean = self.preprocess_text(text1)
        text2_clean = self.preprocess_text(text2)
        
        return {
            'ratio': fuzz.ratio(text1_clean, text2_clean) / 100,
            'partial_ratio': fuzz.partial_ratio(text1_clean, text2_clean) / 100,
            'token_sort_ratio': fuzz.token_sort_ratio(text1_clean, text2_clean) / 100,
            'token_set_ratio': fuzz.token_set_ratio(text1_clean, text2_clean) / 100
        }
    
    def check_similarity_semantic(self, text1: str, text2: str) -> float:
        if not self.sentence_model:
            return 0.0
        
        embeddings = self.sentence_model.encode([text1, text2])
        similarity = util.cos_sim(embeddings[0], embeddings[1])
        return float(similarity[0][0])
    
    def check_similarity_spacy(self, text1: str, text2: str) -> float:
        if not self.nlp:
            return 0.0
        
        doc1 = self.nlp(text1)
        doc2 = self.nlp(text2)
        
        return doc1.similarity(doc2)
    
    def check_ngram_overlap(self, text1: str, text2: str, n: int = 3) -> float:
        text1_clean = self.preprocess_text(text1)
        text2_clean = self.preprocess_text(text2)
        
        ngrams1 = set(self.generate_ngrams(text1_clean, n))
        ngrams2 = set(self.generate_ngrams(text2_clean, n))
        
        if not ngrams1 or not ngrams2:
            return 0.0
        
        intersection = ngrams1.intersection(ngrams2)
        union = ngrams1.union(ngrams2)
        
        return len(intersection) / len(union)
    
    def extract_citations(self, text: str) -> List[str]:
        citations = []
        
        apa_pattern = r'\([A-Za-z\s]+,\s*\d{4}\)|[A-Za-z\s]+\s*\(\d{4}\)'
        apa_citations = re.findall(apa_pattern, text)
        citations.extend(apa_citations)
        
        mla_pattern = r'\([A-Za-z\s]+\s+\d+\)|[A-Za-z\s]+\s+\d+'
        mla_citations = re.findall(mla_pattern, text)
        citations.extend(mla_citations)
        
        chicago_pattern = r'[A-Za-z\s]+,\s*\d{4},\s*\d+'
        chicago_citations = re.findall(chicago_pattern, text)
        citations.extend(chicago_citations)
        
        return citations
    
    def check_citation_format(self, text: str) -> Dict[str, any]:
        citations = self.extract_citations(text)
        
        has_apa = len(re.findall(r'\(\w+\s*,\s*\d{4}\)', text)) > 0
        has_mla = len(re.findall(r'\(\w+\s+\d+\)', text)) > 0
        has_chicago = len(re.findall(r'\w+,\s*\d{4},\s*\d+', text)) > 0
        
        has_references = bool(re.search(r'references|works cited|bibliography', text.lower()))
        
        return {
            'total_citations': len(citations),
            'citations': citations[:10],
            'has_apa_format': has_apa,
            'has_mla_format': has_mla,
            'has_chicago_format': has_chicago,
            'has_references_section': has_references,
            'properly_formatted': len(citations) > 0 and (has_apa or has_mla or has_chicago or has_references)
        }
    
    def add_to_database(self, text: str, metadata: Dict = None):
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        entry = {
            'text': text,
            'hash': text_hash,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat()
        }
        
        filename = f"{self.config['database_path']}/{text_hash}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(entry, f, indent=2)
        
        print(f"✅ Added to database: {filename}")
    
    def load_database(self) -> List[Dict]:
        database = []
        db_path = Path(self.config["database_path"])
        
        for file_path in db_path.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    entry = json.load(f)
                    database.append(entry)
            except:
                continue
        
        return database
    
    def check_against_database(self, text: str) -> List[Dict]:
        database = self.load_database()
        matches = []
        
        for entry in database:
            similarity = self.check_similarity_difflib(text, entry['text'])
            
            if similarity >= self.config["similarity_threshold"]:
                matches.append({
                    'source': entry['metadata'].get('source', 'Unknown'),
                    'similarity': similarity,
                    'text': entry['text'][:200] + '...',
                    'timestamp': entry['timestamp']
                })
        
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        
        return matches
    
    def check_plagiarism(self, text: str, compare_text: Optional[str] = None, 
                        source_name: str = "Unknown") -> Dict:
        
        print(f"\n{'='*60}")
        print(f"🔍 PLAGIARISM CHECK: {source_name}")
        print(f"{'='*60}")
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'source': source_name,
            'text_length': len(text),
            'word_count': len(text.split()),
            'similarity_scores': {},
            'matches': [],
            'suspicious_segments': [],
            'citation_analysis': {},
            'overall_risk': 'LOW',
            'recommendations': []
        }
        
        sentences = self.tokenize_sentences(text)
        result['sentence_count'] = len(sentences)
        
        if compare_text:
            print("\n📊 Comparing with provided text...")
            
            difflib_score = self.check_similarity_difflib(text, compare_text)
            result['similarity_scores']['difflib'] = difflib_score
            
            if self.config["use_fuzzy"]:
                fuzzy_scores = self.check_similarity_fuzzy(text, compare_text)
                result['similarity_scores']['fuzzy'] = fuzzy_scores
            
            if self.config["use_semantic"]:
                semantic_score = self.check_similarity_semantic(text, compare_text)
                result['similarity_scores']['semantic'] = semantic_score
                
                spacy_score = self.check_similarity_spacy(text, compare_text)
                result['similarity_scores']['spacy'] = spacy_score
            
            for n in [2, 3, 4]:
                ngram_score = self.check_ngram_overlap(text, compare_text, n)
                result['similarity_scores'][f'ngram_{n}'] = ngram_score
            
            matcher = difflib.SequenceMatcher(None, text, compare_text)
            for match in matcher.get_matching_blocks():
                if match.size > 20:
                    segment = text[match.a:match.a + match.size]
                    result['suspicious_segments'].append({
                        'text': segment[:100] + '...' if len(segment) > 100 else segment,
                        'length': match.size,
                        'position': match.a
                    })
        
        print("\n📚 Checking against database...")
        db_matches = self.check_against_database(text)
        result['database_matches'] = db_matches[:5]
        
        if self.config["check_citations"]:
            print("\n📝 Analyzing citations...")
            citation_analysis = self.check_citation_format(text)
            result['citation_analysis'] = citation_analysis
        
        risk_score = 0
        if compare_text:
            avg_similarity = np.mean([v for k, v in result['similarity_scores'].items() 
                                     if isinstance(v, (int, float))])
            
            if avg_similarity > self.config["high_similarity"]:
                result['overall_risk'] = 'HIGH'
                result['recommendations'].append("⚠️ Text shows very high similarity - possible direct plagiarism")
                risk_score = 3
            elif avg_similarity > self.config["similarity_threshold"]:
                result['overall_risk'] = 'MEDIUM'
                result['recommendations'].append("⚠️ Text shows moderate similarity - review suspicious segments")
                risk_score = 2
            else:
                result['overall_risk'] = 'LOW'
                result['recommendations'].append("✅ Text appears original")
                risk_score = 1
        
        if self.config["check_citations"]:
            if result['citation_analysis'].get('total_citations', 0) == 0:
                result['recommendations'].append("⚠️ No citations found - consider adding proper references")
            elif not result['citation_analysis'].get('properly_formatted'):
                result['recommendations'].append("⚠️ Citations may be improperly formatted")
        
        result['risk_score'] = risk_score
        
        return result
    
    def generate_report(self, result: Dict, filename: Optional[str] = None) -> str:
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.config['report_path']}/plagiarism_report_{timestamp}.html"
        
        risk_colors = {
            'LOW': '#28a745',
            'MEDIUM': '#ffc107',
            'HIGH': '#dc3545'
        }
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Plagiarism Check Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 30px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #333; border-bottom: 3px solid #007bff; padding-bottom: 10px; }}
                h2 {{ color: #555; margin-top: 30px; }}
                .risk-badge {{ display: inline-block; padding: 5px 15px; border-radius: 20px; font-weight: bold; color: white; background-color: {risk_colors.get(result['overall_risk'], '#6c757d')}; }}
                .score {{ font-size: 24px; font-weight: bold; margin: 10px 0; }}
                .metric {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #007bff; }}
                .suspicious {{ background: #fff3cd; padding: 10px; margin: 5px 0; border-left: 4px solid #ffc107; }}
                .recommendation {{ background: #d4edda; padding: 10px; margin: 5px 0; border-left: 4px solid #28a745; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background: #007bff; color: white; }}
                tr:hover {{ background: #f5f5f5; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔍 Plagiarism Check Report</h1>
                
                <div class="metric">
                    <strong>Source:</strong> {result['source']}<br>
                    <strong>Timestamp:</strong> {result['timestamp']}<br>
                    <strong>Word Count:</strong> {result['word_count']}<br>
                    <strong>Sentences:</strong> {result['sentence_count']}
                </div>
                
                <h2>Overall Risk Assessment <span class="risk-badge">{result['overall_risk']}</span></h2>
        """
        
        if result['similarity_scores']:
            html += """
                <h2>📊 Similarity Scores</h2>
                <table>
                    <tr>
                        <th>Method</th>
                        <th>Score</th>
                    </tr>
            """
            
            for method, score in result['similarity_scores'].items():
                if isinstance(score, dict):
                    for sub_method, sub_score in score.items():
                        color = 'red' if sub_score > 0.8 else 'orange' if sub_score > 0.6 else 'green'
                        html += f"""
                            <tr>
                                <td>{method}.{sub_method}</td>
                                <td style="color: {color};">{sub_score:.2%}</td>
                            </tr>
                        """
                else:
                    color = 'red' if score > 0.8 else 'orange' if score > 0.6 else 'green'
                    html += f"""
                        <tr>
                            <td>{method}</td>
                            <td style="color: {color};">{score:.2%}</td>
                        </tr>
                    """
            
            html += "</table>"
        
        if result['suspicious_segments']:
            html += """
                <h2>⚠️ Suspicious Segments</h2>
            """
            for segment in result['suspicious_segments']:
                html += f"""
                    <div class="suspicious">
                        <strong>Length:</strong> {segment['length']} chars<br>
                        <strong>Text:</strong> "{segment['text']}"
                    </div>
                """
        
        if result.get('database_matches'):
            html += """
                <h2>📚 Database Matches</h2>
                <table>
                    <tr>
                        <th>Source</th>
                        <th>Similarity</th>
                        <th>Text Preview</th>
                    </tr>
            """
            
            for match in result['database_matches']:
                html += f"""
                    <tr>
                        <td>{match['source']}</td>
                        <td>{match['similarity']:.2%}</td>
                        <td>{match['text']}</td>
                    </tr>
                """
            
            html += "</table>"
        
        if result.get('citation_analysis'):
            html += """
                <h2>📝 Citation Analysis</h2>
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
            """
            
            for key, value in result['citation_analysis'].items():
                if key != 'citations':
                    html += f"""
                        <tr>
                            <td>{key.replace('_', ' ').title()}</td>
                            <td>{'✅' if value else '❌' if isinstance(value, bool) else value}</td>
                        </tr>
                    """
            
            html += "</table>"
        
        if result['recommendations']:
            html += """
                <h2>💡 Recommendations</h2>
            """
            for rec in result['recommendations']:
                html += f"""
                    <div class="recommendation">{rec}</div>
                """
        
        html += """
            </div>
        </body>
        </html>
        """
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n📄 Report generated: {filename}")
        return filename

class PlagiarismCLI:
    
    def __init__(self):
        self.checker = PlagiarismChecker()
    
    def run(self):
        print("\n" + "="*60)
        print("🔍 ADVANCED PLAGIARISM CHECKER v2.0")
        print("="*60)
        
        while True:
            print("\n📋 OPTIONS:")
            print("1. Check text against another text")
            print("2. Check text against database")
            print("3. Add text to database")
            print("4. Generate sample report")
            print("5. Batch check multiple files")
            print("6. Exit")
            
            choice = input("\n👉 Select option (1-6): ").strip()
            
            if choice == '1':
                self.check_text_vs_text()
            elif choice == '2':
                self.check_text_vs_database()
            elif choice == '3':
                self.add_to_database()
            elif choice == '4':
                self.generate_sample()
            elif choice == '5':
                self.batch_check()
            elif choice == '6':
                print("\n👋 Goodbye!")
                break
            else:
                print("❌ Invalid option")
    
    def check_text_vs_text(self):
        print("\n📝 Enter first text (or paste):")
        text1 = input().strip()
        
        print("\n📝 Enter second text to compare against:")
        text2 = input().strip()
        
        if text1 and text2:
            result = self.checker.check_plagiarism(text1, text2, "User Comparison")
            self.checker.generate_report(result)
    
    def check_text_vs_database(self):
        print("\n📝 Enter text to check:")
        text = input().strip()
        
        if text:
            result = self.checker.check_plagiarism(text, source_name="Database Check")
            self.checker.generate_report(result)
    
    def add_to_database(self):
        print("\n📝 Enter text to add to database:")
        text = input().strip()
        
        print("\n📝 Enter source name:")
        source = input().strip()
        
        if text and source:
            self.checker.add_to_database(text, {'source': source})
    
    def generate_sample(self):
        print("\n📝 Generating sample report...")
        
        original = """
        Artificial intelligence is transforming the healthcare industry. 
        Machine learning algorithms can analyze medical images with high accuracy.
        Deep learning models are being used to detect diseases early.
        """
        
        suspicious = """
        AI is revolutionizing healthcare sector significantly. 
        Medical images can be analyzed by machine learning algorithms with great precision.
        Early disease detection is being done using deep learning models.
        """
        
        result = self.checker.check_plagiarism(suspicious, original, "Sample Test")
        self.checker.generate_report(result)
    
    def batch_check(self):
        print("\n📁 Enter directory path with text files:")
        dir_path = input().strip()
        
        if os.path.exists(dir_path):
            files = list(Path(dir_path).glob("*.txt"))
            
            if len(files) < 2:
                print("❌ Need at least 2 files for batch check")
                return
            
            print(f"\n📊 Checking {len(files)} files...")
            
            results = []
            for i, file1 in enumerate(files):
                for file2 in files[i+1:]:
                    with open(file1, 'r', encoding='utf-8') as f1, open(file2, 'r', encoding='utf-8') as f2:
                        text1 = f1.read()
                        text2 = f2.read()
                        
                        similarity = self.checker.check_similarity_difflib(text1, text2)
                        
                        results.append({
                            'file1': file1.name,
                            'file2': file2.name,
                            'similarity': similarity
                        })
            
            self.generate_batch_report(results, dir_path)
    
    def generate_batch_report(self, results: List[Dict], dir_path: str):
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Batch Plagiarism Check Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 30px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background: #007bff; color: white; }}
                tr:hover {{ background: #f5f5f5; }}
                .high {{ background: #ffebee; }}
                .medium {{ background: #fff3e0; }}
                .low {{ background: #e8f5e8; }}
            </style>
        </head>
        <body>
            <h1>📊 Batch Plagiarism Check Report</h1>
            <p>Directory: {dir_path}</p>
            <p>Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <table>
                <tr>
                    <th>File 1</th>
                    <th>File 2</th>
                    <th>Similarity</th>
                    <th>Risk Level</th>
                </tr>
        """
        
        for r in results:
            risk = 'HIGH' if r['similarity'] > 0.8 else 'MEDIUM' if r['similarity'] > 0.6 else 'LOW'
            row_class = 'high' if risk == 'HIGH' else 'medium' if risk == 'MEDIUM' else 'low'
            
            html += f"""
                <tr class="{row_class}">
                    <td>{r['file1']}</td>
                    <td>{r['file2']}</td>
                    <td>{r['similarity']:.2%}</td>
                    <td>{risk}</td>
                </tr>
            """
        
        html += """
            </table>
        </body>
        </html>
        """
        
        filename = f"{PLAGIARISM_CONFIG['report_path']}/batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n📄 Batch report generated: {filename}")

def example_usage():
    
    print("\n" + "="*60)
    print("📚 PLAGIARISM CHECKER - EXAMPLE USAGE")
    print("="*60)
    
    checker = PlagiarismChecker()
    
    text1 = """
    The rapid advancement of artificial intelligence has revolutionized 
    multiple industries including healthcare, finance, and transportation.
    Machine learning algorithms can now process vast amounts of data 
    and make predictions with unprecedented accuracy.
    """
    
    text2 = """
    Artificial intelligence's quick progress has transformed various 
    sectors such as medical care, banking, and logistics. 
    Modern machine learning systems analyze enormous datasets 
    and generate forecasts with remarkable precision.
    """
    
    print("\n🔍 Checking plagiarism between two texts...")
    result = checker.check_plagiarism(text1, text2, "Example Comparison")
    
    report_file = checker.generate_report(result)
    
    print(f"\n✅ Example complete! Report saved to: {report_file}")

if __name__ == "__main__":
    import sys
    
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║     🔍 ADVANCED PLAGIARISM CHECKER - Multiple Methods        ║
    ║     Text Matching | Semantic Analysis | N-gram | Citations   ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--example":
            example_usage()
        elif sys.argv[1] == "--cli":
            cli = PlagiarismCLI()
            cli.run()
        else:
            print("Usage: python plagiarism_checker.py [--example | --cli]")
    else:
        cli = PlagiarismCLI()
        cli.run()
