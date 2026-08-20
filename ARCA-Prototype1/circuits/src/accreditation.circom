pragma circom 2.1.6;

include "../node_modules/circomlib/circuits/comparators.circom";

// ARCA — one compliance predicate: "net assets >= accreditation threshold",
// proven WITHOUT revealing net_assets.
//
//   private: net_assets   (the sensitive figure)
//   public:  threshold    (the rule parameter, public and auditable)
//   output:  ok           (1 iff net_assets >= threshold)
//
// This is deliberately the smallest predicate that is still meaningful for the
// paper: it demonstrates privacy-preserving eligibility (Problem Dimension IV)
// and gives you a real prove/verify cost to report.
template Accreditation() {
    signal input net_assets;      // private witness
    signal input threshold;       // public input
    signal output ok;

    // 64-bit range is plenty for a monetary figure in whole currency units.
    component gte = GreaterEqThan(64);
    gte.in[0] <== net_assets;
    gte.in[1] <== threshold;
    ok <== gte.out;

    // Constrain the statement we actually want proven.
    ok === 1;
}

component main { public [threshold] } = Accreditation();
