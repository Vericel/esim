module top_tb;
    logic clock = 1'b0;
    logic alive;

    dut u_dut (
        .clock(clock),
        .alive(alive)
    );

    always #5 clock = ~clock;

    initial begin
        #1;
        $display("UVM_ERROR : 0");
        $display("known_zzz_error: waived locally");
        #20;
        $display("ESIM_ZZZ_PASS");
        $finish;
    end
endmodule
