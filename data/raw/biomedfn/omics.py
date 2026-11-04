# BioMedFn benchmark, domain "omics": computational genomics, transcriptomics and multi-omics utilities.
# Same record format as clinical.py.

PROBLEMS = [
dict(entry="gc_content", source="standard sequence statistic", topic="sequence composition",
sig="def gc_content(seq: str) -> float:",
doc="""
Return the GC content of a DNA sequence in percent, rounded to 2 decimals. The
sequence is case-insensitive; 'N' (unknown base) is ignored, i.e. excluded from
the denominator. Return 0.0 if no A, C, G or T remains. Any other character
raises ValueError.
""",
body="""
s = seq.upper()
if any(c not in 'ACGTN' for c in s):
    raise ValueError('invalid base')
n = sum(1 for c in s if c != 'N')
if n == 0:
    return 0.0
return round(100 * (s.count('G') + s.count('C')) / n, 2)
""",
fault=("n = sum(1 for c in s if c != 'N')", "n = len(s)", "omission"),
examples=[["ATGCGC"], ["acgtnn"]],
tests=[["GGGG"], ["ATATNNNN"], [""], ["NNN"], ["ACGTX"], ["gattacaGCN"]]),

dict(entry="reverse_complement", source="standard sequence operation", topic="sequence manipulation",
sig="def reverse_complement(seq: str) -> str:",
doc="""
Return the reverse complement of a DNA sequence in upper case (A<->T, C<->G,
N->N). The input is case-insensitive; any other character raises ValueError.
""",
body="""
comp = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C', 'N': 'N'}
s = seq.upper()
if any(c not in comp for c in s):
    raise ValueError('invalid base')
return ''.join(comp[c] for c in reversed(s))
""",
fault=("for c in reversed(s))", "for c in s)", "omission"),
examples=[["ATGC"], ["aaccgN"]],
tests=[["GATTACA"], [""], ["NNNA"], ["ACGU"], ["cgcg"]]),

dict(entry="transcribe_dna", source="standard sequence operation", topic="sequence manipulation",
sig="def transcribe_dna(seq: str) -> str:",
doc="""
Return the RNA transcript of a DNA coding-strand sequence: the upper-case
sequence with every T replaced by U. The input is case-insensitive; characters
other than A, C, G, T and N raise ValueError.
""",
body="""
s = seq.upper()
if any(c not in 'ACGTN' for c in s):
    raise ValueError('invalid base')
return s.replace('T', 'U')
""",
fault=("s = seq.upper()", "s = seq", "case"),
examples=[["ATGTTC"], ["gattaca"]],
tests=[["TTTT"], [""], ["AcGt"], ["ATGU"]]),

dict(entry="translate_dna", source="standard genetic code (NCBI table 1)", topic="translation",
sig="def translate_dna(seq: str, to_stop: bool = True) -> str:",
doc="""
Translate a DNA coding sequence (frame 0) into a protein string of one-letter
amino-acid codes with the standard genetic code. Translation reads complete
codons only (a trailing incomplete codon is ignored). Stop codons (TAA, TAG,
TGA) end the translation if to_stop is True; otherwise they are written as '*'.
Codons containing characters other than A, C, G, T are translated as 'X'. The
input is case-insensitive.
""",
body="""
bases = 'TCAG'
aas = 'FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG'
table = {}
i = 0
for b1 in bases:
    for b2 in bases:
        for b3 in bases:
            table[b1 + b2 + b3] = aas[i]
            i += 1
s = seq.upper()
out = []
for j in range(0, len(s) - 2, 3):
    aa = table.get(s[j:j + 3], 'X')
    if aa == '*' and to_stop:
        break
    out.append(aa)
return ''.join(out)
""",
fault=("for j in range(0, len(s) - 2, 3):", "for j in range(0, len(s) - 3, 3):", "off-by-one"),
examples=[["ATGGCCATTGTAATGGGCCGCTGA"], ["atgtaaggg", False]],
tests=[["ATG"], ["ATGTTTTAG"], ["ATGNNNAAATGA", False], [""], ["ATGGA"], ["TGAATG", True], ["CCCGGGTTTAAA"]]),

dict(entry="hamming_distance", source="standard sequence distance", topic="sequence comparison",
sig="def hamming_distance(a: str, b: str) -> int:",
doc="""
Return the number of positions at which two equal-length sequences differ
(case-sensitive comparison). Sequences of different length raise ValueError.
""",
body="""
if len(a) != len(b):
    raise ValueError('sequences must have equal length')
return sum(1 for x, y in zip(a, b) if x != y)
""",
fault=("if len(a) != len(b):\n    raise ValueError('sequences must have equal length')\n", "", "missing check"),
examples=[["GAGCCTACTAACGGGAT", "CATCGTAATGACGGCCT"], ["AAAA", "AAAA"]],
tests=[["", ""], ["ACGT", "TGCA"], ["ACG", "ACGT"], ["aCGT", "ACGT"]]),

dict(entry="kmer_counts", source="standard k-mer counting", topic="sequence composition",
sig="def kmer_counts(seq: str, k: int) -> dict:",
doc="""
Return a dictionary mapping every overlapping k-mer of the upper-case sequence
to its count, skipping k-mers that contain 'N'. k must be at least 1 (otherwise
ValueError); a sequence shorter than k gives an empty dictionary.
""",
body="""
if k < 1:
    raise ValueError('k must be positive')
s = seq.upper()
counts = {}
for i in range(len(s) - k + 1):
    kmer = s[i:i + k]
    if 'N' in kmer:
        continue
    counts[kmer] = counts.get(kmer, 0) + 1
return counts
""",
fault=("for i in range(len(s) - k + 1):", "for i in range(len(s) - k):", "off-by-one"),
examples=[["ATATA", 2], ["acgNacg", 3]],
tests=[["AAAA", 1], ["AC", 3], ["ACGTACGT", 4], ["", 1], ["ACGT", 0], ["NNNN", 2]]),

dict(entry="primer_melting_temp", source="Wallace rule / basic Tm formula", topic="primer design",
sig="def primer_melting_temp(primer: str) -> float:",
doc="""
Return the melting temperature (C) of a DNA primer, rounded to 1 decimal. For
primers of at most 13 nucleotides, Tm = 2 x (A + T) + 4 x (G + C); for longer
primers, Tm = 64.9 + 41 x (G + C - 16.4) / N, with N the primer length. The
primer is case-insensitive; an empty primer or characters other than A, C, G, T
raise ValueError.
""",
body="""
p = primer.upper()
if not p or any(c not in 'ACGT' for c in p):
    raise ValueError('invalid primer')
gc = p.count('G') + p.count('C')
at = len(p) - gc
if len(p) <= 13:
    return round(float(2 * at + 4 * gc), 1)
return round(64.9 + 41 * (gc - 16.4) / len(p), 1)
""",
fault=("if len(p) <= 13:", "if len(p) < 13:", "boundary"),
examples=[["ATGCATGC"], ["AGCTTGCAGTCCGATCGAT"]],
tests=[["ACGTACGTACGTA"], ["GGGGGGGGGGGGGG"], ["atatat"], [""], ["ACGTU"]]),

dict(entry="transition_transversion_ratio", source="standard molecular-evolution statistic", topic="sequence comparison",
sig="def transition_transversion_ratio(seq1: str, seq2: str) -> float:",
doc="""
Return the transition/transversion ratio between two aligned DNA sequences of
equal length, rounded to 3 decimals. Transitions are A<->G and C<->T changes;
all other base changes are transversions. Comparison is case-insensitive.
Unequal lengths, or no transversion, raise ValueError.
""",
body="""
if len(seq1) != len(seq2):
    raise ValueError('sequences must have equal length')
purines, pyrimidines = set('AG'), set('CT')
ts = tv = 0
for x, y in zip(seq1.upper(), seq2.upper()):
    if x == y:
        continue
    if {x, y} <= purines or {x, y} <= pyrimidines:
        ts += 1
    else:
        tv += 1
if tv == 0:
    raise ValueError('no transversions')
return round(ts / tv, 3)
""",
fault=("if {x, y} <= purines or {x, y} <= pyrimidines:", "if {x, y} <= purines:", "omission"),
examples=[["GCAACGCACAACGAAAACCCTTAGGGACTGGATTATTTCGTGATCGTTGTAGTTATTGGAAGTACGGGCATCAACCCAGTT", "TTATCTGACAAAGAAAGCCGTCAACGGCTGGATAATTTCGCGATCGTGCTGGTTACTGGCGGTACGAGTGTTCCTTTGGGT"], ["AAAA", "GGCT"]],
tests=[["ACGT", "GTAC"], ["CCCC", "TTTA"], ["AC", "GT"], ["ACG", "AC"], ["acgt", "ACGA"]]),

dict(entry="cpg_obs_exp", source="Gardiner-Garden & Frommer, J Mol Biol 1987", topic="epigenomics",
sig="def cpg_obs_exp(seq: str) -> float:",
doc="""
Return the observed/expected CpG ratio of a DNA sequence, rounded to 3
decimals: (number of 'CG' dinucleotides x length) / (number of C x number of
G). The sequence is case-insensitive. Return 0.0 if the sequence contains no C
or no G.
""",
body="""
s = seq.upper()
c, g = s.count('C'), s.count('G')
if c == 0 or g == 0:
    return 0.0
return round(s.count('CG') * len(s) / (c * g), 3)
""",
fault=("/ (c * g)", "/ (c + g)", "formula"),
examples=[["CGCGAATT"], ["ACGTTGCA"]],
tests=[["CCCCGGGG"], ["AAAA"], ["cgcgcgcg"], ["GCGCATAT"]]),

dict(entry="motif_positions", source="standard motif search", topic="sequence search",
sig="def motif_positions(seq: str, motif: str) -> list:",
doc="""
Return the 1-based start positions of all (possibly overlapping) occurrences of
a motif in a sequence, in increasing order (case-sensitive). An empty motif
raises ValueError.
""",
body="""
if not motif:
    raise ValueError('empty motif')
return [i + 1 for i in range(len(seq) - len(motif) + 1) if seq[i:i + len(motif)] == motif]
""",
fault=("return [i + 1 for i", "return [i for i", "off-by-one"),
examples=[["GATATATGCATATACTT", "ATAT"], ["AAAA", "AA"]],
tests=[["ACGT", "T"], ["ACGT", "GG"], ["", "A"], ["ACGT", ""], ["TTTTT", "TTT"]]),

dict(entry="consensus_sequence", source="profile consensus", topic="multiple alignment",
sig="def consensus_sequence(seqs: list) -> str:",
doc="""
Return the consensus of equal-length aligned sequences: at each column the most
frequent character, with ties broken alphabetically (the smallest character
wins). An empty list or sequences of different length raise ValueError.
""",
body="""
if not seqs or any(len(s) != len(seqs[0]) for s in seqs):
    raise ValueError('need equal-length sequences')
out = []
for col in zip(*seqs):
    counts = {}
    for c in col:
        counts[c] = counts.get(c, 0) + 1
    best = max(counts.values())
    out.append(min(c for c in counts if counts[c] == best))
return ''.join(out)
""",
fault=("out.append(min(c for c", "out.append(max(c for c", "tie-break"),
examples=[[["ATCCAGCT", "GGGCAACT", "ATGGATCT", "AAGCAACC", "TTGGAACT", "ATGCCATT", "ATGGCACT"]], [["AC", "GT"]]],
tests=[[["A"]], [["AAA", "AAT", "ATT"]], [[]], [["AC", "A"]], [["TG", "CA", "GC"]]]),

dict(entry="phred_to_error_probability", source="Ewing & Green, Genome Res 1998", topic="sequencing quality",
sig="def phred_to_error_probability(q: float) -> float:",
doc="""
Return the base-calling error probability for a Phred quality score,
P = 10^(-Q/10), rounded to 6 decimals. Negative scores raise ValueError.
""",
body="""
if q < 0:
    raise ValueError('quality must be non-negative')
return round(10 ** (-q / 10), 6)
""",
fault=("10 ** (-q / 10)", "10 ** (-q / 20)", "coefficient"),
examples=[[30], [10]],
tests=[[0], [20], [40], [13], [-1]]),

dict(entry="mean_phred_quality", source="FASTQ Phred+33 encoding", topic="sequencing quality",
sig="def mean_phred_quality(quality: str, offset: int = 33) -> float:",
doc="""
Return the mean Phred quality of a FASTQ quality string, rounded to 2
decimals, where each character encodes Q = ord(character) - offset. An empty
string raises ValueError.
""",
body="""
if not quality:
    raise ValueError('empty quality string')
return round(sum(ord(c) - offset for c in quality) / len(quality), 2)
""",
fault=("ord(c) - offset", "ord(c) - 33", "hard-coded"),
examples=[["IIIII"], ["!!5?"]],
tests=[["#"], ["hhhh", 64], ["ABCDEFGHIJ"], [""]]),

dict(entry="assembly_n50", source="standard assembly statistic", topic="genome assembly",
sig="def assembly_n50(contig_lengths: list) -> int:",
doc="""
Return the N50 of a genome assembly: the length L such that contigs of length
>= L contain at least half of the total assembly length (taking the contigs
from longest to shortest, the length of the contig at which the cumulative
length first reaches half of the total). An empty list returns 0.
""",
body="""
if not contig_lengths:
    return 0
total = sum(contig_lengths)
acc = 0
for length in sorted(contig_lengths, reverse=True):
    acc += length
    if acc * 2 >= total:
        return length
return 0
""",
fault=("if acc * 2 >= total:", "if acc * 2 > total:", "boundary"),
examples=[[[2, 3, 4, 5, 6, 7, 8, 9, 10]], [[100, 100]]],
tests=[[[1]], [[5, 5, 5, 5]], [[1000, 1, 1, 1]], [[]], [[50, 30, 20]], [[3, 3, 2, 2]]]),

dict(entry="variant_allele_frequency", source="standard variant-calling statistic", topic="somatic variants",
sig="def variant_allele_frequency(alt_reads: int, total_depth: int) -> float:",
doc="""
Return the variant allele frequency, i.e. the fraction of reads at a position
that support the alternate allele, rounded to 3 decimals. A total depth of zero,
negative counts, or more alternate reads than the depth raise ValueError.
""",
body="""
if total_depth <= 0 or alt_reads < 0 or alt_reads > total_depth:
    raise ValueError('invalid read counts')
return round(alt_reads / total_depth, 3)
""",
fault=("alt_reads / total_depth", "alt_reads / (alt_reads + total_depth)", "formula"),
examples=[[25, 100], [3, 7]],
tests=[[0, 30], [50, 50], [10, 0], [12, 10], [7, 1000]]),

dict(entry="hardy_weinberg_expected", source="Hardy-Weinberg equilibrium", topic="population genetics",
sig="def hardy_weinberg_expected(n_aa: int, n_ab: int, n_bb: int) -> list:",
doc="""
Return the expected genotype counts [AA, AB, BB] under Hardy-Weinberg
equilibrium from observed counts, each rounded to 2 decimals: with N the total
and p the frequency of allele A, (2 n_AA + n_AB) / (2N), the expected counts are
p^2 N, 2 p q N and q^2 N. A total of zero raises ValueError.
""",
body="""
n = n_aa + n_ab + n_bb
if n <= 0:
    raise ValueError('no genotypes')
p = (2 * n_aa + n_ab) / (2 * n)
q = 1 - p
return [round(p * p * n, 2), round(2 * p * q * n, 2), round(q * q * n, 2)]
""",
fault=("round(2 * p * q * n, 2)", "round(p * q * n, 2)", "coefficient"),
examples=[[298, 489, 213], [10, 0, 10]],
tests=[[100, 0, 0], [25, 50, 25], [0, 0, 0], [1, 2, 3]]),

dict(entry="hwe_chi_square", source="Hardy-Weinberg goodness-of-fit test", topic="population genetics",
sig="def hwe_chi_square(n_aa: int, n_ab: int, n_bb: int) -> float:",
doc="""
Return the chi-square statistic for departure from Hardy-Weinberg equilibrium,
rounded to 3 decimals: the sum over the three genotypes of
(observed - expected)^2 / expected, with expected counts p^2 N, 2pqN and q^2 N;
genotypes with an expected count of zero are skipped. A total of zero raises
ValueError.
""",
body="""
n = n_aa + n_ab + n_bb
if n <= 0:
    raise ValueError('no genotypes')
p = (2 * n_aa + n_ab) / (2 * n)
q = 1 - p
exp = [p * p * n, 2 * p * q * n, q * q * n]
chi = 0.0
for o, e in zip((n_aa, n_ab, n_bb), exp):
    if e > 0:
        chi += (o - e) ** 2 / e
return round(chi, 3)
""",
fault=("chi += (o - e) ** 2 / e", "chi += abs(o - e) / e", "formula"),
examples=[[298, 489, 213], [50, 0, 50]],
tests=[[25, 50, 25], [100, 0, 0], [10, 80, 10], [0, 0, 0]]),

dict(entry="tpm_normalize", source="Wagner et al., Theory Biosci 2012", topic="transcriptomics",
sig="def tpm_normalize(counts: list, lengths_bp: list) -> list:",
doc="""
Return transcripts per million (TPM) for each gene, rounded to 2 decimals:
divide each read count by the gene length in kilobases, then scale these rates
so that they sum to one million. Lists of different length, a non-positive
length or a total rate of zero raise ValueError.
""",
body="""
if len(counts) != len(lengths_bp) or any(l <= 0 for l in lengths_bp):
    raise ValueError('invalid input')
rates = [c / (l / 1000) for c, l in zip(counts, lengths_bp)]
total = sum(rates)
if total == 0:
    raise ValueError('no reads')
return [round(r / total * 1e6, 2) for r in rates]
""",
fault=("rates = [c / (l / 1000) for c, l in zip(counts, lengths_bp)]", "rates = [float(c) for c, l in zip(counts, lengths_bp)]", "omission"),
examples=[[[10, 20, 30], [1000, 2000, 3000]], [[100, 0, 50], [500, 1000, 2500]]],
tests=[[[5], [100]], [[1, 1], [1000, 4000]], [[0, 0], [100, 100]], [[3, 4], [100]], [[10, 20], [1500, 0]]]),

dict(entry="rpkm", source="Mortazavi et al., Nat Methods 2008", topic="transcriptomics",
sig="def rpkm(gene_reads: int, gene_length_bp: int, total_mapped_reads: int) -> float:",
doc="""
Return reads per kilobase of transcript per million mapped reads (RPKM),
rounded to 2 decimals: reads x 10^9 / (gene length in bp x total mapped reads).
Non-positive length or total raises ValueError.
""",
body="""
if gene_length_bp <= 0 or total_mapped_reads <= 0:
    raise ValueError('invalid input')
return round(gene_reads * 1e9 / (gene_length_bp * total_mapped_reads), 2)
""",
fault=("gene_reads * 1e9", "gene_reads * 1e6", "unit"),
examples=[[500, 2000, 10000000], [0, 1000, 5000000]],
tests=[[1200, 1500, 20000000], [7, 300, 1000000], [10, 0, 100]]),

dict(entry="log2_fold_change", source="standard differential-expression effect size", topic="transcriptomics",
imports="import math",
sig="def log2_fold_change(control: float, treated: float, pseudocount: float = 1.0) -> float:",
doc="""
Return the log2 fold change of treated versus control expression with a
pseudocount, log2((treated + pseudocount) / (control + pseudocount)), rounded to
3 decimals. Negative expression values or a non-positive pseudocount raise
ValueError.
""",
body="""
if control < 0 or treated < 0 or pseudocount <= 0:
    raise ValueError('invalid input')
return round(math.log2((treated + pseudocount) / (control + pseudocount)), 3)
""",
fault=("math.log2(", "math.log(", "log base"),
examples=[[10.0, 40.0], [0.0, 0.0]],
tests=[[100.0, 25.0], [3.0, 7.0, 0.5], [0.0, 1023.0], [5.0, -1.0]]),

dict(entry="benjamini_hochberg", source="Benjamini & Hochberg, JRSS B 1995", topic="multiple testing",
sig="def benjamini_hochberg(pvalues: list) -> list:",
doc="""
Return Benjamini-Hochberg adjusted p-values (q-values) in the original order,
each rounded to 4 decimals. For the p-value of rank i (1 = smallest) among m
p-values, the adjusted value is the minimum over ranks j >= i of p_(j) x m / j,
capped at 1. An empty list returns []; p-values outside [0, 1] raise ValueError.
""",
body="""
m = len(pvalues)
if any(p < 0 or p > 1 for p in pvalues):
    raise ValueError('p-values must be in [0, 1]')
order = sorted(range(m), key=lambda i: pvalues[i])
adj = [0.0] * m
running = 1.0
for rank in range(m, 0, -1):
    i = order[rank - 1]
    running = min(running, pvalues[i] * m / rank)
    adj[i] = running
return [round(a, 4) for a in adj]
""",
fault=("running = min(running, pvalues[i] * m / rank)", "running = min(1.0, pvalues[i] * m / rank)", "missing monotonicity"),
examples=[[[0.01, 0.04, 0.03, 0.2]], [[0.5]]],
tests=[[[]], [[0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205]], [[0.9, 0.8, 0.95]], [[0.02, 0.02, 0.5]], [[0.1, 1.2]]]),

dict(entry="zscore_normalize", source="standard normalisation", topic="multi-omics preprocessing",
sig="def zscore_normalize(values: list) -> list:",
doc="""
Return the z-scores (x - mean) / sd of a list of values, each rounded to 3
decimals, where sd is the population standard deviation (dividing by n). Fewer
than two values or a standard deviation of zero raise ValueError.
""",
body="""
n = len(values)
if n < 2:
    raise ValueError('need at least two values')
mean = sum(values) / n
sd = (sum((x - mean) ** 2 for x in values) / n) ** 0.5
if sd == 0:
    raise ValueError('zero variance')
return [round((x - mean) / sd, 3) for x in values]
""",
fault=("/ n) ** 0.5", "/ (n - 1)) ** 0.5", "estimator"),
examples=[[[1.0, 2.0, 3.0]], [[10.0, 10.0, 20.0, 40.0]]],
tests=[[[5.0, 5.0]], [[0.0, 1.0]], [[3.5]], [[-2.0, 0.0, 2.0, 4.0, 6.0]]]),

dict(entry="tumor_mutational_burden", source="Chalmers et al., Genome Med 2017", topic="precision oncology",
sig="def tumor_mutational_burden(n_mutations: int, covered_bases: int) -> float:",
doc="""
Return the tumour mutational burden in mutations per megabase of covered
sequence, rounded to 2 decimals. Non-positive coverage or a negative number of
mutations raises ValueError.
""",
body="""
if covered_bases <= 0 or n_mutations < 0:
    raise ValueError('invalid input')
return round(n_mutations / (covered_bases / 1e6), 2)
""",
fault=("covered_bases / 1e6", "covered_bases / 1e3", "unit"),
examples=[[10, 1000000], [17, 1100000]],
tests=[[0, 30000000], [300, 30000000], [5, 0], [1, 2500000]]),

dict(entry="alt_allele_frequency", source="genotype-based allele frequency", topic="population genetics",
sig="def alt_allele_frequency(genotypes: list) -> float:",
doc="""
Return the alternate-allele frequency from diploid genotype calls '0/0', '0/1'
and '1/1', rounded to 3 decimals. Missing calls './.' are ignored. Return 0.0 if
no genotype is called; any other string raises ValueError.
""",
body="""
alt = {'0/0': 0, '0/1': 1, '1/1': 2}
called = 0
n_alt = 0
for g in genotypes:
    if g == './.':
        continue
    if g not in alt:
        raise ValueError('unknown genotype')
    called += 1
    n_alt += alt[g]
if called == 0:
    return 0.0
return round(n_alt / (2 * called), 3)
""",
fault=("    if g == './.':\n        continue\n", "    if g == './.':\n        called += 1\n        continue\n", "missing data"),
examples=[[["0/0", "0/1", "1/1", "0/1"]], [["0/1", "./.", "./."]]],
tests=[[[]], [["./."]], [["1/1", "1/1"]], [["0/0", "0|1"]], [["0/1", "0/0", "0/0", "./.", "0/0"]]]),

dict(entry="percent_identity", source="pairwise alignment statistic", topic="sequence alignment",
sig="def percent_identity(aligned_a: str, aligned_b: str) -> float:",
doc="""
Return the percent identity of two aligned sequences of equal length, rounded
to 2 decimals: identical non-gap columns divided by the number of columns in
which at least one sequence has a residue (columns with a gap '-' in both
sequences are ignored; a gap opposite a residue counts as a mismatch). Unequal
lengths raise ValueError; if no column remains return 0.0.
""",
body="""
if len(aligned_a) != len(aligned_b):
    raise ValueError('aligned sequences must have equal length')
cols = [(x, y) for x, y in zip(aligned_a, aligned_b) if not (x == '-' and y == '-')]
if not cols:
    return 0.0
same = sum(1 for x, y in cols if x == y and x != '-')
return round(100 * same / len(cols), 2)
""",
fault=("if not (x == '-' and y == '-')]", "if x != '-' and y != '-']", "gap handling"),
examples=[["ACGT-A", "ACGTTA"], ["AC--", "AG--"]],
tests=[["----", "----"], ["ACGT", "ACGT"], ["A-C-", "-A-C"], ["ACG", "AC"], ["MKV-LL", "MRVALL"]]),

dict(entry="cigar_reference_length", source="SAM format specification", topic="read alignment",
sig="def cigar_reference_length(cigar: str) -> int:",
doc="""
Return the number of reference bases spanned by an alignment with the given
SAM CIGAR string: the sum of the lengths of the operations that consume the
reference (M, D, N, = and X); I, S, H and P do not. An invalid CIGAR string
raises ValueError; '*' or an empty string returns 0.
""",
body="""
if cigar in ('', '*'):
    return 0
total = 0
num = ''
for ch in cigar:
    if ch.isdigit():
        num += ch
    elif ch in 'MIDNSHP=X' and num:
        if ch in 'MDN=X':
            total += int(num)
        num = ''
    else:
        raise ValueError('invalid CIGAR')
if num:
    raise ValueError('invalid CIGAR')
return total
""",
fault=("if ch in 'MDN=X':", "if ch in 'MIDN=X':", "operation set"),
examples=[["10M2I5M"], ["3S20M1D10M100N5M"]],
tests=[["*"], ["50M"], ["5H10=2X3D"], ["M10"], ["10M5"], ["4I"]]),

dict(entry="polygenic_risk_score", source="additive polygenic score", topic="precision medicine",
sig="def polygenic_risk_score(dosages: list, betas: list) -> float:",
doc="""
Return an additive polygenic risk score, the sum of effect-allele dosage times
effect size over all variants, rounded to 4 decimals. Dosages must lie in
[0, 2]; lists of different length or a dosage outside [0, 2] raise ValueError.
""",
body="""
if len(dosages) != len(betas):
    raise ValueError('length mismatch')
if any(d < 0 or d > 2 for d in dosages):
    raise ValueError('dosage out of range')
return round(sum(d * b for d, b in zip(dosages, betas)), 4)
""",
fault=("if len(dosages) != len(betas):\n    raise ValueError('length mismatch')\n", "", "missing check"),
examples=[[[0, 1, 2], [0.1, -0.2, 0.05]], [[1.5, 0.2], [0.3, 0.7]]],
tests=[[[], []], [[2, 2, 2], [0.01, 0.02, 0.03]], [[1, 2], [0.5]], [[3], [0.1]], [[0.5, 1.0, 1.5, 2.0], [-0.12, 0.08, 0.0, 0.25]]]),

dict(entry="protein_gravy", source="Kyte & Doolittle, J Mol Biol 1982", topic="proteomics",
sig="def protein_gravy(protein: str) -> float:",
doc="""
Return the grand average of hydropathy (GRAVY) of a protein sequence, rounded
to 3 decimals: the mean Kyte-Doolittle hydropathy of its residues (A 1.8,
R -4.5, N -3.5, D -3.5, C 2.5, Q -3.5, E -3.5, G -0.4, H -3.2, I 4.5, L 3.8,
K -3.9, M 1.9, F 2.8, P -1.6, S -0.8, T -0.7, W -0.9, Y -1.3, V 4.2). The
sequence is case-insensitive; an empty sequence or an unknown residue raises
ValueError.
""",
body="""
kd = {'A': 1.8, 'R': -4.5, 'N': -3.5, 'D': -3.5, 'C': 2.5, 'Q': -3.5, 'E': -3.5, 'G': -0.4, 'H': -3.2, 'I': 4.5,
      'L': 3.8, 'K': -3.9, 'M': 1.9, 'F': 2.8, 'P': -1.6, 'S': -0.8, 'T': -0.7, 'W': -0.9, 'Y': -1.3, 'V': 4.2}
p = protein.upper()
if not p or any(c not in kd for c in p):
    raise ValueError('invalid protein sequence')
return round(sum(kd[c] for c in p) / len(p), 3)
""",
fault=("'I': 4.5,", "'I': 4.2,", "table entry"),
examples=[["MKTAYIAKQR"], ["ilv"]],
tests=[["G"], ["WWWW"], ["ACDEFGHIKLMNPQRSTVWY"], [""], ["MKB"], ["IIIAAA"]]),

dict(entry="longest_orf_length", source="open reading frame search", topic="gene finding",
sig="def longest_orf_length(dna: str) -> int:",
doc="""
Return the length in nucleotides of the longest open reading frame on the
forward strand of a DNA sequence, searching all three frames: an ORF starts with
ATG and ends with the first in-frame stop codon (TAA, TAG or TGA), which is
included in the length. Return 0 if there is no complete ORF. The sequence is
case-insensitive.
""",
body="""
s = dna.upper()
stops = {'TAA', 'TAG', 'TGA'}
best = 0
for i in range(len(s) - 2):
    if s[i:i + 3] != 'ATG':
        continue
    for j in range(i, len(s) - 2, 3):
        if s[j:j + 3] in stops:
            best = max(best, j + 3 - i)
            break
return best
""",
fault=("for i in range(len(s) - 2):", "for i in range(0, len(s) - 2, 3):", "frame"),
examples=[["ATGAAATAG"], ["CCATGCCCTGAATGTAA"]],
tests=[["ATGCCC"], [""], ["atgtga"], ["GATGAAAAAATAGATGTAA"], ["TTATGTTTTTTTTTAGATG"]]),

dict(entry="kmer_jaccard", source="k-mer sketch similarity", topic="sequence comparison",
sig="def kmer_jaccard(a: str, b: str, k: int) -> float:",
doc="""
Return the Jaccard similarity of the sets of overlapping k-mers of two
sequences (case-insensitive), |A intersect B| / |A union B|, rounded to 3
decimals. k must be at least 1 (otherwise ValueError); if both sets are empty
return 0.0.
""",
body="""
if k < 1:
    raise ValueError('k must be positive')
sa = {a.upper()[i:i + k] for i in range(len(a) - k + 1)}
sb = {b.upper()[i:i + k] for i in range(len(b) - k + 1)}
union = sa | sb
if not union:
    return 0.0
return round(len(sa & sb) / len(union), 3)
""",
fault=("return round(len(sa & sb) / len(union), 3)", "return round(len(sa & sb) / min(len(sa), len(sb)), 3) if sa and sb else 0.0", "formula"),
examples=[["ACGTACGT", "ACGTTT", 3], ["AAAA", "aaaa", 2]],
tests=[["A", "C", 2], ["ACGT", "TGCA", 1], ["ACGTAC", "ACG", 3], ["AC", "AC", 0], ["GGGCCC", "GGGTTTCCC", 2]]),
]
