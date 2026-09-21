// Fixture: timespec whitespace placeholder (see rtl/lintfail.v)
module lintfail(input clk, output y);
  wire unused_w1;       // never used -> %Warning-UNUSEDSIGNAL
  wire unused_w2;
  assign unused_w1 = clk & unused_w2;
  assign y = 1'b0;
endmodule
