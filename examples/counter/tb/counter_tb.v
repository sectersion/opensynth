`timescale 1ns/1ps

// Self-checking testbench for counter.
// Convention (see skills/verify-rtl): increments errors on mismatch,
// prints PASS/FAIL summary line, exits with $fatal when tests fail.

module counter_tb;

    localparam WIDTH = 8;
    localparam CLK_PERIOD = 10;

    reg clk = 0;
    reg rst_n = 0;
    reg enable = 0;
    wire [WIDTH-1:0] count;

    counter #(.WIDTH(WIDTH)) dut (
        .clk    (clk),
        .rst_n  (rst_n),
        .enable (enable),
        .count  (count)
    );

    always #(CLK_PERIOD/2) clk = ~clk;

    integer errors = 0;
    integer expected;
    integer i;

    // reference model
    reg [WIDTH-1:0] model;
    initial model = {WIDTH{1'b0}};

    task check;
        input [WIDTH-1:0] exp;
        begin
            if (count !== exp) begin
                $display("FAIL: count=%0d expected=%0d @%0t", count, exp, $time);
                errors = errors + 1;
            end
        end
    endtask

    integer num_checks = 0;

    initial begin
        // settle, then check reset value on first negedge
        @(negedge clk);
        check(model); num_checks = num_checks + 1;

        // release reset
        rst_n = 1;

        // count 0..9 with enable
        for (i = 0; i < 10; i = i + 1) begin
            enable = 1;
            @(negedge clk);
            model = model + 1;
            check(model); num_checks = num_checks + 1;
        end

        // pause: enable low, count must hold
        enable = 0;
        @(negedge clk);
        check(model); num_checks = num_checks + 1;
        @(negedge clk);
        check(model); num_checks = num_checks + 1;

        // sync reset: returns to zero
        rst_n = 0;
        @(negedge clk);
        model = {WIDTH{1'b0}};
        check(model); num_checks = num_checks + 1;
        rst_n = 1;
        @(negedge clk);
        check(model); num_checks = num_checks + 1;

        if (errors == 0) begin
            $display("PASS: %0d checks, 0 errors", num_checks);
        end else begin
            $display("FAIL: %0d checks, %0d errors", num_checks, errors);
            $fatal(1, "testbench failed");
        end
        $finish;
    end

endmodule
