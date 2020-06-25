package py5.core;

import java.nio.ByteBuffer;
import java.nio.IntBuffer;
import java.util.HashSet;
import java.util.Set;

import com.jogamp.newt.event.KeyListener;
import com.jogamp.newt.event.MouseListener;
import com.jogamp.newt.event.WindowListener;

import processing.core.PApplet;
import processing.core.PImage;
import processing.event.MouseEvent;

public class Py5Applet extends PApplet {

  protected Py5Methods py5Methods;
  protected Set<String> py5RegisteredEvents;

  public static final char CODED = PApplet.CODED;

  public void usePy5Methods(Py5Methods py5Methods) {
    this.py5Methods = py5Methods;
    this.py5RegisteredEvents = new HashSet<String>();
    for (Object m : py5Methods.get_function_list())
      this.py5RegisteredEvents.add(m.toString());
  }

  @Override
  public void settings() {
    py5Methods.run_method("settings");
  }

  @Override
  public void setup() {
    py5Methods.run_method("setup");
  }

  @Override
  public void draw() {
    if (py5RegisteredEvents.contains("draw"))
      py5Methods.run_method("draw");
    else
      noLoop();
  }

  @Override
  public void mousePressed() {
    if (py5RegisteredEvents.contains("mouse_pressed"))
      py5Methods.run_method("mouse_pressed");
  }

  @Override
  public void mouseReleased() {
    if (py5RegisteredEvents.contains("mouse_released"))
      py5Methods.run_method("mouse_released");
  }

  @Override
  public void mouseClicked() {
    if (py5RegisteredEvents.contains("mouse_clicked"))
      py5Methods.run_method("mouse_clicked");
  }

  @Override
  public void mouseDragged() {
    if (py5RegisteredEvents.contains("mouse_dragged"))
      py5Methods.run_method("mouse_dragged");
  }

  @Override
  public void mouseMoved() {
    if (py5RegisteredEvents.contains("mouse_moved"))
      py5Methods.run_method("mouse_moved");
  }

  @Override
  public void mouseEntered() {
    if (py5RegisteredEvents.contains("mouse_entered"))
      py5Methods.run_method("mouse_entered");
  }

  @Override
  public void mouseExited() {
    if (py5RegisteredEvents.contains("mouse_exited"))
      py5Methods.run_method("mouse_exited");
  }

  @Override
  public void mouseWheel(MouseEvent event) {
    if (py5RegisteredEvents.contains("mouse_wheel"))
      py5Methods.run_method("mouse_wheel", event);
  }

  @Override
  public void keyPressed() {
    if (py5RegisteredEvents.contains("key_pressed"))
      py5Methods.run_method("key_pressed");
  }

  @Override
  public void keyReleased() {
    if (py5RegisteredEvents.contains("key_released"))
      py5Methods.run_method("key_released");
  }

  @Override
  public void keyTyped() {
    if (py5RegisteredEvents.contains("key_typed"))
      py5Methods.run_method("key_typed");
  }

  @Override
  public void exitActual() {
    if (py5RegisteredEvents.contains("exit_actual"))
      py5Methods.run_method("exit_actual");

    final Object nativeWindow = surface.getNative();
    if (nativeWindow instanceof com.jogamp.newt.Window) {
      com.jogamp.newt.Window window = (com.jogamp.newt.Window) nativeWindow;
      // remove the listeners before destroying window to prevent a core dump
      for (WindowListener l : window.getWindowListeners()) {
        window.removeWindowListener(l);
      }
      for (KeyListener l : window.getKeyListeners()) {
        window.removeKeyListener(l);
      }
      for (MouseListener l : window.getMouseListeners()) {
        window.removeMouseListener(l);
      }
      window.destroy();
    } else {
      surface.setVisible(false);
    }
  }

  public float getFrameRate() {
    return frameRate;
  }

  public boolean isKeyPressed() {
    return keyPressed;
  }

  public byte[] loadAndGetPixels() {
    loadPixels();
    ByteBuffer byteBuffer = ByteBuffer.allocate(4 * pixels.length);
    IntBuffer intBuffer = byteBuffer.asIntBuffer();
    intBuffer.put(pixels);

    return byteBuffer.array();
  }

  public void setAndUpdatePixels(byte[] newPixels) {
    ByteBuffer byteBuffer = ByteBuffer.allocate(newPixels.length);
    byte[] byteArray = byteBuffer.array();
    System.arraycopy(newPixels, 0, byteArray, 0, newPixels.length);
    IntBuffer intBuffer = byteBuffer.asIntBuffer();

    intBuffer.get(pixels);
    updatePixels();
  }

  public PImage convertBytesToPImage(byte[] pixels, int width, int height) {
    if (pixels.length != 4 * width * height) {
      throw new RuntimeException("byte size incorrect");
    }

    PImage image = new PImage(width, height, ARGB);
    image.parent = this; // make save() work

    ByteBuffer.wrap(pixels).asIntBuffer().get(image.pixels);

    return image;
  }

}
