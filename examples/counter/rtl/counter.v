// counter.v — 8-bit free-running up counter with sync active-high enable and reset.
// Reference example for the opensynth flow: spec -> RTL -> tested RTL -> GDSII.

module counter #(
    parameter WIDTH = 8
) (
    input  wire             clk,
    input  wire             rst_n,   // synchronous, active-low
    input  wire             enable,
    output wire [WIDTH-1:0] count
);

    reg [WIDTH-1:0] count_q;

    always @(posedge clk) begin
        if (!rst_n)
            count_q <= {WIDTH{1'b0}};
        else if (enable)
            count_q <= count_q + 1'b1;
    end

    assign count = count_q;

endmodule
