package com.termux.view;

import java.util.Arrays;

/** Plain-Java test of the RTL row layout (no Android needed). Run by CI after the patch is applied. */
public class LayoutTest {
    static void check(String name, float[] w, boolean[] r, float[] expect) {
        float[] out = new float[w.length];
        RtlRunLayout.layout(w, r, w.length, out);
        if (!Arrays.equals(out, expect)) throw new RuntimeException(name + ": got " + Arrays.toString(out));
        System.out.println("ok " + name);
    }

    public static void main(String[] a) {
        check("mixed", new float[]{10, 14, 8}, new boolean[]{true, false, true}, new float[]{22, 8, 0});
        check("pure", new float[]{13}, new boolean[]{true}, new float[]{0});
        check("rtl-split", new float[]{5, 6}, new boolean[]{true, true}, new float[]{6, 0});
        check("ltr-split", new float[]{4, 3, 2}, new boolean[]{true, false, false}, new float[]{5, 0, 3});
        check("prefix-neutral", new float[]{2, 9}, new boolean[]{false, true}, new float[]{9, 0});
    }
}
