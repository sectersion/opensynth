// Fixture: prints FAIL then PASS (rc 0) -- sim.py must fail on the FAIL line.
`timescale 1ns/1ps
module simfail_tb;
  reg clk = 0;
  wire y;
  simfail u0(.clk(clk), .y(y));

  initial begin
    $display("FAIL: intentional fixture failure");
    $display("PASS: decoy line (must not mask the FAIL above)");
    #1 $finish;
  end

  always #5 clk = ~clk;
endmodule
