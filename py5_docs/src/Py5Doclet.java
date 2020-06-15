import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

import javax.lang.model.SourceVersion;
import javax.lang.model.element.Element;
import javax.lang.model.element.ElementKind;
import javax.lang.model.element.TypeElement;
import javax.lang.model.util.ElementFilter;

import jdk.javadoc.doclet.Doclet;
import jdk.javadoc.doclet.DocletEnvironment;
import jdk.javadoc.doclet.Reporter;

import com.sun.source.util.DocTrees;
import com.sun.source.doctree.DocTree;
import com.sun.source.doctree.ParamTree;
import com.sun.source.doctree.SeeTree;
import com.sun.source.doctree.ReturnTree;
import com.sun.source.doctree.DeprecatedTree;
import com.sun.source.doctree.ThrowsTree;
import com.sun.source.doctree.UnknownBlockTagTree;
import com.sun.source.doctree.DocCommentTree;

public class Py5Doclet implements Doclet {
    Reporter reporter;

    @Override
    public void init(Locale locale, Reporter reporter) {
        this.reporter = reporter;
    }

    public void printElement(DocTrees trees, String partOf, Element e) {
        ElementKind kind = e.getKind();
        String name = e.getSimpleName().toString();

        DocCommentTree docCommentTree = trees.getDocCommentTree(e);
        if (docCommentTree != null) {
            System.out.println("******************************************");
            System.out.println("(" + kind + ") " + partOf + "." + name);

            System.out.println("{{Entire body}}");
            for (DocTree tree : docCommentTree.getFullBody()) {
                String s = tree.toString();
                s = s.replaceAll("\\( begin auto-generated from .*?\\)", "");
                s = s.replaceAll("\\( end auto-generated \\)", "");
                s = s.trim();
                s = s.replace("\n", "");
                s = s.replace("<br/>", "\n");
                s = s.replace("<BR>", "\n");
                s = s.replace("<nobr>", "");
                s = s.replace("</nobr>", "");
                s = s.replace("<NOBR>", "");
                s = s.replace("</NOBR>", "");
                s = s.replace("<b>", " `");
                s = s.replace("</b>", "` ");
                s = s.replace("<PRE>", "\n\n```\n");
                s = s.replace("</PRE>", "\n```\n\n");
                s = s.replace("<TT>", "\n\n```\n");
                s = s.replace("</TT>", "\n```\n\n");
                s = s.replace("<h3>", "\n\n");
                s = s.replace("</h3>", "\n--------\n\n");
                s = s.replace("<P>", "\n\n");
                s = s.replace("<p>", "\n\n");
                s = s.replace("<p/>", "\n\n");
                System.out.print(s);
            }

            System.out.println("\n{{Block tags}}");
            for (DocTree tree : docCommentTree.getBlockTags()) {
                switch (tree.getKind()) {
                    case PARAM:
                        ParamTree param = (ParamTree) tree;
                        String pname = param.getName().toString();
                        String desc = param.getDescription().toString();
                        String istype = param.isTypeParameter() ? " (type)" : "";
                        System.out.println("Param: " + pname + istype + ": " + desc);
                        break;
                    case SEE:
                        SeeTree see = (SeeTree) tree;
                        String reference = see.getReference().toString();
                        System.out.println("See Also: " + reference);
                        break;
                    case RETURN:
                        ReturnTree ret = (ReturnTree) tree;
                        String retDesc = ret.getDescription().toString();
                        System.out.println("Returns: " + retDesc);
                        break;
                    case THROWS:
                        ThrowsTree throwsTree = (ThrowsTree) tree;
                        String throwDesc = throwsTree.getDescription().toString();
                        String eName = throwsTree.getExceptionName().toString();
                        System.out.println("Throws: " + eName + " " + throwDesc);
                        break;
                    case DEPRECATED:
                        DeprecatedTree dep = (DeprecatedTree) tree;
                        String reason = dep.getBody().toString();
                        System.out.println("Deprecated: " + reason);
                        break;
                    case UNKNOWN_BLOCK_TAG:
                        UnknownBlockTagTree unknown = (UnknownBlockTagTree) tree;
                        String tagname = unknown.getTagName().toString();
                        String content = unknown.getContent().toString();
                        System.out.println("Unknown: " + tagname + " " + content);
                        break;
                    default:
                        System.out.println("???? DEFAULT ????");
                        System.out.println(tree.getKind());
                        System.out.println(tree.toString());
                }
            }
        }
    }

    @Override
    public boolean run(DocletEnvironment docEnv) {
        DocTrees docTrees = docEnv.getDocTrees();
        for (TypeElement t : ElementFilter.typesIn(docEnv.getIncludedElements())) {
            System.out.println(t.getKind() + ":" + t);
            for (Element e : t.getEnclosedElements()) {
                printElement(docTrees, t.toString(), e);
            }
        }
        return true;
    }

    @Override
    public String getName() {
        return "Py5Doclet";
    }

    @Override
    public Set<? extends Option> getSupportedOptions() {
        Option[] options = { new Option() {
            private final List<String> someOption = Arrays.asList("-overviewfile", "--overview-file", "-o");

            @Override
            public int getArgumentCount() {
                return 1;
            }

            @Override
            public String getDescription() {
                return "an option with aliases";
            }

            @Override
            public Option.Kind getKind() {
                return Option.Kind.STANDARD;
            }

            @Override
            public List<String> getNames() {
                return someOption;
            }

            @Override
            public String getParameters() {
                return "file";
            }

            @Override
            public boolean process(String opt, List<String> arguments) {
                return true;
            }
        } };
        return new HashSet<Option>(Arrays.asList(options));
    }

    @Override
    public SourceVersion getSupportedSourceVersion() {
        // support the latest release
        return SourceVersion.latest();
    }
}
