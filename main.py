import streamlit as st
from PIL import Image
import numpy as np
import io



class TemplateDisplacement:
    """
    Class to handle image displacement effects for t-shirt designs
    """
    def __init__(self, template_image):
        """
        Initialize with a template image
        Args:
            template_image: PIL Image object of the template
        """
        self.template = template_image.convert('RGBA')
        self.displacement_map = None
        self.selected_area = None
        
    def create_displacement_map(self):
        """Create grayscale displacement map from template"""
        gray = self.template.convert('L')
        self.displacement_map = np.array(gray)
    
    def set_selected_area(self, x1, y1, x2, y2):
        """
        Set the area where the graphic will be placed
        Args:
            x1, y1: Top-left corner coordinates
            x2, y2: Bottom-right corner coordinates
        """
        # Ensure coordinates are within image boundaries
        width, height = self.template.size
        x1 = max(0, min(x1, width))
        y1 = max(0, min(y1, height))
        x2 = max(0, min(x2, width))
        y2 = max(0, min(y2, height))
        
        # Ensure x2 > x1 and y2 > y1
        if x2 < x1:
            x1, x2 = x2, x1
        if y2 < y1:
            y1, y2 = y2, y1
            
        self.selected_area = (x1, y1, x2, y2)
    
    def place_graphic(self, graphic_image, scale_factor=1.0):
        """
        Place and displace graphic on template
        Args:
            graphic_image: PIL Image object of the graphic
            scale_factor: Float to scale the graphic
        Returns:
            PIL Image of the result
        """
        if self.selected_area is None:
            raise ValueError("No area selected")
        
        x1, y1, x2, y2 = self.selected_area
        area_width = x2 - x1
        area_height = y2 - y1
        
        # Convert to int to prevent floating point errors
        area_width = int(area_width)
        area_height = int(area_height)
        
        # Resize graphic according to scale factor and selected area
        graphic = graphic_image.convert('RGBA')
        scaled_width = int(area_width * scale_factor)
        scaled_height = int(area_height * scale_factor)
        
        # Maintain aspect ratio
        original_aspect = graphic.width / graphic.height
        target_aspect = scaled_width / scaled_height
        
        if original_aspect > target_aspect:
            scaled_width = int(scaled_height * original_aspect)
        else:
            scaled_height = int(scaled_width / original_aspect)
            
        graphic = graphic.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
        
        # Center the graphic in the selected area
        x_offset = x1 + (area_width - scaled_width) // 2
        y_offset = y1 + (area_height - scaled_height) // 2
        
        # Get displacement map region
        disp_region = self.displacement_map[y1:y2, x1:x2]
        
        # Create result image
        result = self.template.copy()
        
        # Apply displacement
        graphic_array = np.array(graphic)
        displaced = np.zeros_like(graphic_array)
        
        try:
            for y in range(scaled_height):
                for x in range(scaled_width):
                    # Scale coordinates to match displacement map
                    map_x = int(x * (area_width / scaled_width))
                    map_y = int(y * (area_height / scaled_height))
                    
                    if map_y >= disp_region.shape[0] or map_x >= disp_region.shape[1]:
                        continue
                    
                    # Calculate displacement
                    disp_amount = disp_region[map_y, map_x] / 255.0
                    crease_intensity = 1 - disp_amount
                    crease_intensity = np.power(crease_intensity, 1.5)
                    
                    # Apply wave-like displacement for realistic fabric effect
                    new_x = int(x + crease_intensity * 8 * np.sin(y / 10))
                    new_y = int(y + crease_intensity * 6)
                    
                    # Ensure coordinates stay within bounds
                    new_x = min(max(new_x, 0), scaled_width - 1)
                    new_y = min(max(new_y, 0), scaled_height - 1)
                    
                    displaced[new_y, new_x] = graphic_array[y, x]
                    
        except IndexError as e:
            st.error(f"Error during displacement calculation: {str(e)}")
            return None
            
        # Convert back to PIL Image and paste onto template
        displaced_image = Image.fromarray(displaced)
        result.paste(displaced_image, (x_offset, y_offset), displaced_image)
        
        return result


def main():
    """Main application function"""
    st.set_page_config(page_title="T-shirt Design Displacement Tool", 
                      layout="wide",
                      initial_sidebar_state="collapsed")
    
    st.title("T-shirt Design Displacement Tool")
    
    # Add instructions
    with st.expander("📖 How to Use"):
        st.markdown("""
        1. **Upload Template**: Start by uploading your t-shirt template image
        2. **Select Area**: Draw a rectangle on the template where you want to place your design
        3. **Upload Design**: Upload the graphic you want to place on the template
        4. **Adjust Size**: Use the slider to resize your design
        5. **Download**: When satisfied, download your final design
        
        **Tips**:
        - For best results, use a template with visible creases and folds
        - Make sure your graphic has a transparent background (PNG format)
        - The scale slider helps you perfect the size of your design
        """)
    
    # Step 1: Upload displacement map
    st.header("1. Upload Template")
    template_file = st.file_uploader(
        "Choose your t-shirt template...", 
        type=['png', 'jpg', 'jpeg'],
        help="Upload a t-shirt template with visible creases and folds"
    )
    
    if template_file is not None:
        try:
            template_image = Image.open(template_file)
            template = TemplateDisplacement(template_image)
            template.create_displacement_map()
            
            # Step 2: Select area on displacement map
            st.header("2. Select Design Area")
            st.write("Draw a rectangle on the image to select where you want to place your design:")
            
            # Display template image
            st.image(template_image, use_container_width=True)
            
            # Create columns for coordinate input
            col1, col2 = st.columns(2)
            with col1:
                x1 = st.number_input("Left Position (X1)", 0, template_image.width, int(template_image.width * 0.25))
                y1 = st.number_input("Top Position (Y1)", 0, template_image.height, int(template_image.height * 0.25))
            with col2:
                x2 = st.number_input("Right Position (X2)", 0, template_image.width, int(template_image.width * 0.75))
                y2 = st.number_input("Bottom Position (Y2)", 0, template_image.height, int(template_image.height * 0.75))
            
            # Process selected area
            if x1 < x2 and y1 < y2:
                
                template.set_selected_area(x1, y1, x2, y2)
                
                # Step 3: Upload graphic
                st.header("3. Upload Your Design")
                design_file = st.file_uploader(
                    "Choose your design...", 
                    type=['png', 'jpg', 'jpeg'],
                    help="Upload the graphic you want to place on the template"
                )
                
                if design_file is not None:
                    try:
                        design_image = Image.open(design_file)
                        
                        # Step 4: Resize controls
                        st.header("4. Adjust Design Size")
                        scale_factor = st.slider(
                            "Scale Factor", 
                            0.1, 2.0, 1.0, 0.1,
                            help="Adjust the size of your design"
                        )
                        
                        # Process and display result
                        result = template.place_graphic(design_image, scale_factor)
                        
                        if result is not None:
                            st.header("Final Result")
                            st.image(result, use_container_width=True)
                            
                            # Add download button
                            buf = io.BytesIO()
                            result.save(buf, format="PNG")
                            st.download_button(
                                label="💾 Download Final Design",
                                data=buf.getvalue(),
                                file_name="final_design.png",
                                mime="image/png",
                                help="Download your completed design"
                            )
                        
                    except Exception as e:
                        st.error(f"Error processing design: {str(e)}")
                        st.write("Please try uploading a different design image.")
                        
        except Exception as e:
            st.error(f"Error processing template: {str(e)}")
            st.write("Please try uploading a different template image.")


if __name__ == "__main__":
    main()