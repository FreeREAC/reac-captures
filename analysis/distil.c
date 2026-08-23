// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Pau Aliagas <linuxnow@gmail.com>

/* Distil one REAC capture: keep every control frame, keep sampled contiguous
 * runs of audio, drop the rest.
 *
 * WHY THIS EXISTS. The raw corpus is 47.9 GB and 44.9M REAC frames, of which
 * 37.9M are FILLER — frames whose control block says nothing and whose only
 * payload is one 8-sample audio slice. The bulk is there; the protocol
 * information is not. A corpus that cannot be committed cannot gate anything on
 * a machine that does not have the rig, so it is distilled to the part that
 * carries evidence.
 *
 * THE RULE, and why each half of it is safe:
 *
 *   1. A frame whose control block classifies as anything other than FILLER is
 *      KEPT — all 6.9M of them, none dropped, no sampling, no dedup. It is kept
 *      TRUNCATED TO 50 BYTES: ethernet[0:14] | counter[14:16] | type[16:18] |
 *      control block[18:50]. Fifty is not a guess — it is REAC_CTRL_BLOCK_END,
 *      the offset where audio starts, so those 50 bytes are the whole of what
 *      any control reader ever looks at. reac_ctrl_parse, the block checksum,
 *      the head-amp record, the declared port table and the box identity all
 *      read inside [0:50] and every one of them returns the same answer over the
 *      truncated frame as over the whole one.
 *
 *      The pcap record keeps its ORIGINAL origlen, so the frame still says how
 *      long it was on the wire. That is what makes this honest rather than a
 *      forgery: caplen < origlen is the pcap-level statement "this was captured
 *      with a snaplen", which is exactly what happened, and both corpus gates
 *      already treat such a record as a control block with no audio — the corpus
 *      has always contained captures taken at snaplen 64/128/200/400 and they
 *      are first-class in it.
 *
 *   2. Audio is SAMPLED: --runs contiguous runs of --run-len whole frames, per
 *      distinct wire geometry, spaced evenly through the file. Per GEOMETRY
 *      because a REAC file interleaves streams of different widths (40ch
 *      downstream 1492 B, 16ch upstream 628 B, 8ch 340 B, 32ch 1204 B) and a
 *      run must be contiguous WITHIN the stream it samples. Evenly SPACED
 *      because the head of a capture is the establish handshake and the audio
 *      worth decoding is in the steady state after it. CONTIGUOUS because braid
 *      and lane defects appear as a relationship between adjacent frames; a
 *      scatter of isolated frames cannot show one.
 *
 *   3. A record that is not a 0x8819 frame at all is kept WHOLE. There are 23 in
 *      the corpus and they are cheaper to keep than to explain.
 *
 * WHAT MOVES AND WHAT MUST NOT. Dropping filler moves records/reac/filler; the
 * 50-byte cut moves trunc/offlen and the dn=/up= audio tallies. NOTHING ELSE MAY
 * MOVE. Every per-class control count, every checksum tally, the head-amp
 * counts, the declared port table and the box match are properties of frames
 * this tool keeps in full-fidelity form, so they are identical before and after,
 * and the baseline diff is checked field-by-field to prove it.
 *
 * Timestamps are copied verbatim, never regenerated: the counter-contiguity and
 * clock-drift findings rest on them. So is the pcap global header, so link-type,
 * endianness and the file's own snaplen survive.
 */
#include <reac/reac.h>
#include <reac/reac_ctrlblk.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define KEEP_LEN REAC_CTRL_BLOCK_END   /* 50 — one past the control block */
#define MAXGEO 32
#define MAXFRAME 65536

static const uint8_t MAGIC_US_LE[4] = {0xd4,0xc3,0xb2,0xa1};
static const uint8_t MAGIC_US_BE[4] = {0xa1,0xb2,0xc3,0xd4};
static const uint8_t MAGIC_NS_LE[4] = {0x4d,0x3c,0xb2,0xa1};
static const uint8_t MAGIC_NS_BE[4] = {0xa1,0xb2,0x3c,0x4d};

struct geo { uint32_t origlen; unsigned long total; unsigned long seen; };

/* One pass over the record headers to learn how many whole frames each geometry
 * has, so the runs can be spaced through the file instead of piled at its head.
 * A single-pass tool would have to guess, and every guess puts the sample where
 * the establish traffic is. */
static int survey(const char *path, int swap, struct geo *g, int *ng,
                  unsigned long *nrec)
{
	FILE *f = fopen(path, "rb");
	if (!f) return -1;
	if (fseek(f, 24, SEEK_SET) != 0) { fclose(f); return -1; }
	uint8_t h[16];
	*ng = 0; *nrec = 0;
	while (fread(h, 1, 16, f) == 16) {
		uint32_t caplen, origlen;
		memcpy(&caplen, h + 8, 4); memcpy(&origlen, h + 12, 4);
		if (swap) { caplen = __builtin_bswap32(caplen); origlen = __builtin_bswap32(origlen); }
		if (caplen > MAXFRAME) { fclose(f); return -1; }
		(*nrec)++;
		if (fseek(f, (long)caplen, SEEK_CUR) != 0) break;
		int i;
		for (i = 0; i < *ng; i++) if (g[i].origlen == origlen) break;
		if (i == *ng) {
			if (*ng == MAXGEO) continue;
			g[*ng].origlen = origlen; g[*ng].total = 0; g[*ng].seen = 0; (*ng)++;
		}
		g[i].total++;
	}
	fclose(f);
	return 0;
}

/* Is this the n-th whole frame of its geometry inside one of the sampled runs?
 * The runs are laid out so run r covers [r*span, r*span+run_len) where span
 * divides the geometry's population evenly. */
static int in_run(unsigned long idx, unsigned long total,
                  unsigned runs, unsigned run_len)
{
	if (total <= (unsigned long)runs * run_len) return 1;  /* small: keep it all */
	unsigned long span = total / runs;
	for (unsigned r = 0; r < runs; r++) {
		unsigned long start = r * span;
		if (idx >= start && idx < start + run_len) return 1;
	}
	return 0;
}

int main(int argc, char **argv)
{
	const char *in = NULL, *out = NULL;
	unsigned runs = 4, run_len = 250;
	for (int i = 1; i < argc; i++) {
		if (!strcmp(argv[i], "--runs") && i + 1 < argc) runs = (unsigned)atoi(argv[++i]);
		else if (!strcmp(argv[i], "--run-len") && i + 1 < argc) run_len = (unsigned)atoi(argv[++i]);
		else if (!in) in = argv[i];
		else out = argv[i];
	}
	if (!in || !out || runs == 0) {
		fprintf(stderr, "usage: distil [--runs N] [--run-len N] <in.pcap> <out.pcap>\n");
		return 2;
	}

	FILE *f = fopen(in, "rb");
	if (!f) { fprintf(stderr, "distil: cannot open %s\n", in); return 1; }
	uint8_t gh[24];
	if (fread(gh, 1, 24, f) != 24) { fprintf(stderr, "distil: %s: short header\n", in); fclose(f); return 1; }
	int swap;
	if (!memcmp(gh, MAGIC_US_LE, 4) || !memcmp(gh, MAGIC_NS_LE, 4)) swap = 0;
	else if (!memcmp(gh, MAGIC_US_BE, 4) || !memcmp(gh, MAGIC_NS_BE, 4)) swap = 1;
	else { fprintf(stderr, "distil: %s: not a classic pcap\n", in); fclose(f); return 1; }

	struct geo g[MAXGEO]; int ng; unsigned long nrec;
	if (survey(in, swap, g, &ng, &nrec) < 0) {
		fprintf(stderr, "distil: %s: survey failed\n", in); fclose(f); return 1;
	}

	FILE *o = fopen(out, "wb");
	if (!o) { fprintf(stderr, "distil: cannot write %s\n", out); fclose(f); return 1; }
	fwrite(gh, 1, 24, o);   /* link-type, endianness and snaplen ride along */

	static uint8_t buf[MAXFRAME];
	unsigned long kept_ctrl = 0, kept_audio = 0, kept_other = 0, dropped = 0;
	uint8_t h[16];
	while (fread(h, 1, 16, f) == 16) {
		uint32_t caplen, origlen;
		memcpy(&caplen, h + 8, 4); memcpy(&origlen, h + 12, 4);
		if (swap) { caplen = __builtin_bswap32(caplen); origlen = __builtin_bswap32(origlen); }
		if (caplen > MAXFRAME) break;
		if (fread(buf, 1, caplen, f) != caplen) break;

		struct reac_ctrl_parsed p;
		enum reac_ctrl_kind k = reac_ctrl_parse(buf, caplen, &p);

		int whole = 0, keep = 0;
		if (k == REAC_CTRL_NONE) {          /* not a REAC frame at all */
			keep = 1; whole = 1; kept_other++;
		} else {
			/* The run window is computed over EVERY record of the geometry, not
			 * only the whole ones. A capture taken at a snaplen has no whole
			 * frames at all, and sampling only those emptied such a file
			 * completely: 400 truncated filler records went to zero and the
			 * file stopped covering anything. Filler that carries no audio
			 * still carries the classification that says it is filler, and it
			 * costs 50 bytes to keep a representative run of it. */
			int in = 0;
			int i;
			for (i = 0; i < ng; i++) if (g[i].origlen == origlen) break;
			if (i < ng) {
				in = in_run(g[i].seen, g[i].total, runs, run_len);
				g[i].seen++;
			}
			if (k != REAC_CTRL_FILLER) {
				/* every control frame, always; whole when it falls in a run so
				 * the sampled audio stays contiguous across it */
				keep = 1; whole = (in && caplen == origlen); kept_ctrl++;
			} else if (in) {
				keep = 1; whole = (caplen == origlen); kept_audio++;
			} else {
				dropped++;
			}
		}
		if (!keep) continue;

		uint32_t wcap = whole ? caplen : (caplen < KEEP_LEN ? caplen : KEEP_LEN);
		uint8_t oh[16];
		memcpy(oh, h, 8);                       /* the timestamp, byte for byte */
		uint32_t wc = swap ? __builtin_bswap32(wcap) : wcap;
		uint32_t wo = swap ? __builtin_bswap32(origlen) : origlen;
		memcpy(oh + 8, &wc, 4);
		memcpy(oh + 12, &wo, 4);                /* the WIRE length is preserved */
		fwrite(oh, 1, 16, o);
		fwrite(buf, 1, wcap, o);
	}
	fclose(f);
	if (fclose(o) != 0) { fprintf(stderr, "distil: %s: write failed\n", out); return 1; }

	/* AN EMPTY OUTPUT IS NOT A SMALL ONE. A file distilled to nothing looks
	 * exactly like a clean pass to anything that scans the corpus afterwards,
	 * so say it here rather than let a gate call the silence agreement. */
	if (nrec > 0 && kept_ctrl + kept_audio + kept_other == 0) {
		fprintf(stderr, "distil: %s: %lu records in, NOTHING KEPT — refusing\n", in, nrec);
		return 1;
	}

	printf("%s records=%lu kept_ctrl=%lu kept_audio=%lu kept_other=%lu dropped=%lu\n",
	       in, nrec, kept_ctrl, kept_audio, kept_other, dropped);
	return 0;
}
