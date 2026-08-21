/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (C) 2026 Pau Aliagas <linuxnow@gmail.com>
 *
 * Per-slot RMS of a box's upstream FILLERs, decoded through libreac.
 *
 * THE honest wire-audio probe: a plain PipeWire lane read is meaningless here (the REAC
 * braid is frame-global, and pw-record's channelmix lies about per-port silence), so a
 * claim about which box inputs carry audio has to come from the frames themselves.
 *
 * It prints EVERY fabric slot the frame actually carries, not a fixed 16 — an earlier cut
 * accumulated 40 slots and printed the first 16, which would have reported "the upper bank
 * is silent" for a box that had merely placed it elsewhere in the ring. The reported
 * `upstream_channels` is what makes the printed range checkable.
 *
 * Reading the numbers, on this rig: about -106 dBFS is mathematical zero (nothing is
 * converting into that slot), about -89 dBFS is an idle preamp's own noise floor (the slot
 * is live and converting), and anything well above that is signal.
 *
 * Capture (box upstream only, so our own TX cannot be mistaken for the box's answer):
 *   sudo timeout 6 tcpdump -i <nic> -c 300 -w up.pcap \
 *        'ether proto 0x8819 and ether src <box-mac>'
 * Build:
 *   gcc up_slots.c -o up_slots -I<libreac>/include <libreac>/libreac.a -lm
 */
#include <reac/reac.h>
#include <reac/reac_upstream.h>
#include <stdio.h>
#include <math.h>

#define MAX_SLOTS  40   /* the REAC fabric ring: 5 groups x 8 */
#define SAMPLES    12   /* PCM samples per channel per frame */

int main(int argc, char **argv)
{
	if (argc < 2) { fprintf(stderr, "usage: %s <pcap>\n", argv[0]); return 2; }
	FILE *f = fopen(argv[1], "rb");
	if (!f) { perror(argv[1]); return 1; }

	unsigned char gh[24];
	if (fread(gh, 1, 24, f) != 24) { fclose(f); return 1; }

	double sum[MAX_SLOTS] = {0};
	long   cnt[MAX_SLOTS] = {0};
	int frames = 0, slots = -1;

	while (frames < 400) {
		unsigned char ph[16];
		if (fread(ph, 1, 16, f) != 16) break;
		unsigned incl = ph[8] | ph[9] << 8 | ph[10] << 16 | (unsigned)ph[11] << 24;
		unsigned char buf[2048];
		if (incl > sizeof buf) { fseek(f, incl, SEEK_CUR); continue; }
		if (fread(buf, 1, incl, f) != incl) break;

		size_t len = reac_frame_clean_len(incl);
		int nch = reac_upstream_channels(len);
		if (nch <= 0 || nch > MAX_SLOTS) continue;
		if (buf[16] != 0x00 || buf[17] != 0x00) continue;   /* FILLER only: pure audio */

		unsigned char pcm[MAX_SLOTS * SAMPLES * 3];
		if (reac_upstream_decode(buf, len, pcm) != SAMPLES) continue;
		frames++;
		slots = nch;

		for (int c = 0; c < nch; c++)
			for (int s = 0; s < SAMPLES; s++) {
				const unsigned char *p = &pcm[(size_t)(c * SAMPLES + s) * 3];
				int v = p[0] | p[1] << 8 | p[2] << 16;
				if (v & 0x800000) v |= ~0xffffff;
				double x = v / 8388608.0;
				sum[c] += x * x;
				cnt[c]++;
			}
	}
	fclose(f);

	printf("filler frames decoded: %d\n", frames);
	printf("upstream_channels: %d\n", slots);
	for (int c = 0; c < MAX_SLOTS; c++) {
		if (!cnt[c]) continue;
		double rms = sqrt(sum[c] / cnt[c]);
		printf("slot %2d: %6.1f dBFS\n", c + 1, 20 * log10(rms > 1e-10 ? rms : 1e-10));
	}
	return 0;
}
