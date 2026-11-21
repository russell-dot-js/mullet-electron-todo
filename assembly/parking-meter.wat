;; Right to park a pending obligation in one of the sixteen reserved spaces.
;; Last hearing's total feeds the next hearing's parking meter.
(module
  (func (export "assess") (param $seal i32) (param $hearing i32)
        (param $space i32) (param $arrears i32) (result i32)
    local.get $seal
    local.get $hearing
    i32.const 17
    i32.mul
    i32.add
    local.get $arrears
    i32.xor
    local.get $space
    i32.const 11
    i32.add
    i32.rem_u
    i32.const 1
    i32.add))
