from Parser import Parser, lex
from semantic_analyzer import SemanticAnalyzer, SemanticError
import pprint
from InterCodeGenerator import *

#所有测试用例（program_1_1 ~ program_9_2）
tests = [
  ("program_1_1", """fn program_1_1() {}"""),
  ("program_1_2", """fn program_1_2() { ;;;;;; }"""),
  ("program_1_3", """fn program_1_3() { return; }"""),
  ("program_1_4", """fn program_1_4(mut a:i32) {}"""),
  ("program_1_5__1", """fn program_1_5__1() -> i32 { return 1; }"""),
  ("program_1_5__2_invalid", """fn program_1_5__2() -> i32 { return; }"""),
  ("program_1_5__3_invalid", """fn program_1_5__3() { return 1; }"""),

  ("program_2_1__1", """fn program_2_1__1() { let mut a:i32; }"""),
  ("program_2_1__2_invalid", """fn program_2_1__2() { let mut b; }"""),
  ("program_2_1__3", """fn program_2_1__3() { let mut a:i32; let mut a; let mut a:i32; }"""),
  ("program_2_2__1", """fn program_2_2__1(mut a:i32) { a = 32; }"""),
  ("program_2_2__2_invalid", """fn program_2_2__2() { a = 32; }"""),
  ("program_2_3__1", """fn program_2_3__1() { let mut a:i32=1; let mut b=1; }"""),
  ("program_2_3__2_invalid", """fn program_2_3__2() { let mut b:i32=a; }"""),
  ("program_2_3__3_invalid", """fn program_2_3__3() { let mut a:i32; let mut b:i32=a; }"""),
  ("program_2_3__4", """fn program_2_3__4() { let mut a:i32=1; let mut a=2; let mut a:i32=3; }"""),

  ("program_3_1__1", """fn program_3_1__1() { 0; (1); ((2)); (((3))); }"""),
  ("program_3_1__2", """fn program_3_1__2(mut a:i32) { a; (a); ((a)); (((a))); }"""),
  ("program_3_2", """fn program_3_2() { 1*2/3; 4+5/6; 7<8; 9>10; 11==12; 13!=14; 1*2+3*4!=4/2-3/1; }"""),
  ("program_3_3__1", """fn program_3_3__1() {}"""),
  ("program_3_3__2", """fn program_3_3__2() { program_3_3__1(); } fn program_3_3__1() {}"""),
  ("program_3_3__3_invalid", """fn program_3_3__3() { program_3_3__1(1); } fn program_3_3__1() {}"""),
  ("program_3_3__4_invalid", """fn program_3_3__4() { program_3_3__4(program_3_3__4); } fn program_3_3__4(a:i32) {}"""),

  ("program_4_1__1", """fn program_4_1__1(mut a:i32) -> i32 { if a>0 { return 1; } }"""),
  ("program_4_1__2", """fn program_4_1__2(mut a:i32) -> i32 { if a>0 { return 1; } else { return 0; } }"""),
  ("program_4_2", """fn program_4_2(mut a:i32) -> i32 { if a>0 { return a+1; } else if a<0 { return a-1; } else { return 0; } }"""),

  ("program_5_1", """fn program_5_1(mut n:i32) { while n>0 { n=n-1; } }"""),
  ("program_5_2", """fn program_5_2(mut n:i32) { for mut i in 1..n+1 { n=n-1; } }"""),
  ("program_5_3", """fn program_5_3() { loop { } }"""),
  ("program_5_4__1", """fn program_5_4__1() { while 1==1 { break; } }"""),
  ("program_5_4__2_invalid", """fn program_5_4__2() { break; }"""),
  ("program_5_4__3", """fn program_5_4__3() { while 1==0 { continue; } }"""),
  ("program_5_4__4_invalid", """fn program_5_4__4() { continue; }"""),

  ("program_6_1__2_invalid", """fn program_6_1__2() { let c:i32=1; c=2; }"""),
  ("program_6_2__1", """fn program_6_2__1() { let mut a:i32=1; let mut b:&mut i32=&mut a; let mut c:i32=*b; }"""),
  ("program_6_2__2", """fn program_6_2__2() { let a:i32=1; let b:& i32=&a; let c:i32=*b; }"""),
  ("program_6_2__3_invalid", """fn program_6_2__3() { let mut a:i32=1; let mut b=*a; }"""),
  ("program_6_2__4_invalid", """fn program_6_2__4() { let mut a:i32=1; let b=&a; let mut c=&mut a; }"""),
  ("program_6_2__5_invalid", """fn program_6_2__5() { let a:i32=1; let mut b=&mut a; }"""),
  ("program_6_2__6", """fn program_6_2__6() { let mut a:i32=1; let b=&a; let c=&a; }"""),

  ("program_7_1", """fn program_7_1(mut x:i32,mut y:i32) { let mut z={ let mut t=x*x+x; t=t+x*y; t }; }"""),
  ("program_7_2", """fn program_7_2(mut x:i32,mut y:i32) -> i32 { let mut t=x*x+x; t=t+x*y; t }"""),
  ("program_7_3", """fn program_7_3(mut a:i32) { let mut b=if a>0 {1} else {0}; }"""),
  ("program_7_4__1", """fn program_7_4__1() { let mut a=loop { break 1; }; }"""),
  ("program_7_4__2_invalid", """fn program_7_4__2() { break 2; }"""),

  ("program_8_1__1", """fn program_8_1__1() { let mut a:[i32;3]; a=[1,2,3]; }"""),
  ("program_8_1__2_invalid", """fn program_8_1__2(mut a:i32) { let mut a:[i32;2]; a=1; }"""),
  ("program_8_1__3_invalid", """fn program_8_1__3(mut a:i32) { let mut a:[i32;2]; a=[1,2,3]; }"""),
  ("program_8_1__4_invalid", """fn program_8_1__4() { let mut a=[[i32;1];1]; a=[1]; }"""),

  ("program_8_2__1", """fn program_8_2__1(mut a:[i32;3]) { let mut b:i32=a[0]; a[0]=1; }"""),
  ("program_8_2__2_invalid", """fn program_8_2__2(mut a:i32) { let mut a=[1,2,3]; let mut b=a[a]; }"""),
  ("program_8_2__3_invalid", """fn program_8_2__3() { let mut a=[1,2,3]; let mut b=a[3]; }"""),
  ("program_8_2__4_invalid", """fn program_8_2__4() { let a:[i32;3]=[1,2,3]; a[0]=4; }"""),

  ("program_9_1__1", """fn program_9_1__1() { let a:(i32,i32,i32); a=(1,2,3); }"""),
  ("program_9_1__2_invalid", """fn program_9_1__2(mut a:i32) { let mut a:(i32,i32); a=1; }"""),
  ("program_9_1__3_invalid", """fn program_9_1__3(mut a:i32) { let mut a:(i32,i32); a=(1,2,3); }"""),
  ("program_9_1__4_invalid", """fn program_9_1__4() { let mut a=((i32,i32),); a=(1,); }"""),
  ("program_9_2__1", """fn program_9_2__1(mut a:(i32,i32)) { let mut b:i32=a.0; a.0=1; }"""),
  ("program_9_2__2_invalid", """fn program_9_2__2(mut a:i32) { let mut a=(1,2,3); let mut b=a.a; }"""),
  ("program_9_2__3_invalid", """fn program_9_2__3() { let mut a=(1,2,3); let mut b=a.3; }"""),
  ("program_9_2__4_invalid", """fn program_9_2__4() { let a:(i32,i32,i32)=(1,2,3); a.0=4; }"""),
]

def run_tests():
  total, passed = 0, 0
  for name, source in tests:
    total += 1
    print(f"\n=== Test: {name} ===")
    try:
      tokens = lex(source)
      parser = Parser(tokens)
      ast = parser.parse()
      pprint.pprint(ast, width=120, indent=2)

      analyzer = SemanticAnalyzer(ast)
      analyzer.analyze()
      print("✅ 成功通过语义分析")


      if "invalid" in name:
        print(f"❌ {name}: 错误程序未检查出")
      else:
        # 程序正确，进行中间代码生成
        generator = QuadrupleGenerator(ast)
        quadruples = generator.generate()
        # 打印结果
        for i, quad in enumerate(quadruples):
          print(f"{quad}")
        passed += 1

    except SemanticError as e:
      if "invalid" in name:
        print(f"✅ 成功检查出程序的错误: {e}")
        passed += 1
      else:
        print(f"❌ 正确程序检查出意料之外的错误: {e}")
    except Exception as e:
      print(f"❌ 其他异常: {e}")

  print(f"\n✅ Summary: {passed}/{total} passed")

if __name__ == "__main__":
  run_tests()
